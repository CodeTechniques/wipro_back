from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import UserCommittee
from .services.roi_service import calculate_total_return


@api_view(["GET"])
def user_roi_view(request, committee_id):
    user_committee = UserCommittee.objects.get(
        user=request.user,
        committee_id=committee_id
    )

    data = calculate_total_return(user_committee)
    return Response(data)



from django.http import JsonResponse
from .models import Committee
from committees.services.roi_service import calculate_committee_return

def committee_list(request):
    committees = Committee.objects.filter(is_active=True)

    data = []
    for c in committees:
        roi_data = calculate_committee_return(c)
        data.append({
            "id": c.id,
            "name": c.name,

            # ✅ all three options together
            "daily_amount": float(c.daily_amount) if c.daily_amount is not None else None,
            "monthly_amount": float(c.monthly_amount) if c.monthly_amount is not None else None,
            "yearly_amount": float(c.yearly_amount) if c.yearly_amount is not None else None,

            "duration_months": c.duration_months,
            "roi_percent": float(c.roi_percent),

            # 👇 NEW CALCULATED FIELDS
            "total_invested": float(roi_data["total_invested"]),
            "expected_roi": float(roi_data["roi_amount"]),
            "expected_total_return": float(roi_data["total_return"]),

            "total_slots": c.total_slots,
            "filled_slots": c.filled_slots,
            "slots_available": c.total_slots - c.filled_slots,
        })

    return JsonResponse(data, safe=False)





from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from .models import Committee, UserCommittee
from django.contrib.auth.models import User
from rest_framework_simplejwt.authentication import JWTAuthentication
from decimal import Decimal

from committees.models import Committee, UserCommittee
from wallet.models import Wallet, PaymentTransaction
from wallet.calculations import calculate_net_balance_for_user
from wallet.services import debit_wallet

@csrf_exempt
@require_POST
def join_committee(request, committee_id):
    jwt_authenticator = JWTAuthentication()
    auth_result = jwt_authenticator.authenticate(request)

    if auth_result is None:
        return JsonResponse({"error": "Authentication required"}, status=401)

    user, _ = auth_result

    try:
        with transaction.atomic():

            committee = Committee.objects.select_for_update().get(
                id=committee_id,
                is_active=True
            )

            # ❌ Slot full
            if committee.filled_slots >= committee.total_slots:
                return JsonResponse(
                    {"error": "No slots available"},
                    status=400
                )

            # ❌ Already joined
            if UserCommittee.objects.filter(
                user=user,
                committee=committee,
                is_active=True
            ).exists():
                return JsonResponse(
                    {"error": "You already joined this committee"},
                    status=400
                )

            # ---------------------------------
            # 💰 DETERMINE JOIN AMOUNT
            # ---------------------------------
            if committee.daily_amount:
                join_amount = Decimal(committee.daily_amount)
                join_type = "daily"
            elif committee.monthly_amount:
                join_amount = Decimal(committee.monthly_amount)
                join_type = "monthly"
            elif committee.yearly_amount:
                join_amount = Decimal(committee.yearly_amount)
                join_type = "yearly"
            else:
                return JsonResponse(
                    {"error": "Committee joining amount not defined"},
                    status=400
                )

            # ---------------------------------
            # 💰 WALLET CHECK
            # ---------------------------------
            wallet, _ = Wallet.objects.get_or_create(user=user)

            available_balance = (
                calculate_net_balance_for_user(user)
                + wallet.bonus_balance
            )

            if available_balance < join_amount:
                return JsonResponse(
                    {
                        "error": "Insufficient wallet balance",
                        "required": float(join_amount),
                        "available": float(available_balance),
                    },
                    status=400
                )

            # ---------------------------------
            # 🔥 DEDUCT MONEY
            # ---------------------------------
            debit_wallet(
                wallet=wallet,
                amount=join_amount,
                tx_type="committee_investment",
                source="system",
                reference_id=f"committee_join_{committee.id}",
                note=f"Joined committee ({join_type}): {committee.name}",
            )

            # ---------------------------------
            # ✅ CREATE USER COMMITTEE
            # ---------------------------------
            user_committee = UserCommittee.objects.create(
                user=user,
                committee=committee,
                total_invested=join_amount
            )

            # ---------------------------------
            # 🔥 AUTO ASSIGN PLAN
            # ---------------------------------
            from committees.models import CommitteePaymentPlan, UserCommitteePlan
            from django.utils.timezone import now
            from datetime import timedelta

            committee_plan = CommitteePaymentPlan.objects.filter(
                committee=committee,
                is_active=True
            ).select_related("plan").first()

            if committee_plan:
                plan = committee_plan.plan

                UserCommitteePlan.objects.create(
                    user_committee=user_committee,
                    plan=plan,
                    next_payment_due=now() + timedelta(days=plan.interval_days),
                    is_active=True
                )

            # ---------------------------------
            # UPDATE SLOT COUNT
            # ---------------------------------
            committee.filled_slots += 1
            committee.save(update_fields=["filled_slots"])

            return JsonResponse({
                "success": True,
                "message": "Successfully joined committee",
                "committee_id": committee.id,
                "user_committee_id": user_committee.id,
                "amount_deducted": float(join_amount),
                "plan_type": join_type,
                "plan_auto_created": True if committee_plan else False,
            })

    except Committee.DoesNotExist:
        return JsonResponse(
            {"error": "Committee not found or inactive"},
            status=404
        )

@api_view(["POST"])
def pay_due(request, user_committee_id):

    # 🔐 AUTH
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)
    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    # 🔎 GET PLAN
    try:
        user_plan = UserCommitteePlan.objects.select_related(
            "plan",
            "user_committee",
            "user_committee__committee"
        ).get(
            user_committee_id=user_committee_id,
            user_committee__user=user,
            is_active=True
        )
    except UserCommitteePlan.DoesNotExist:
        return JsonResponse(
            {"error": "No active plan found"},
            status=404
        )

    # 🔴 CHECK IF DUE
    if user_plan.next_payment_due > now():
        return JsonResponse({
            "error": "No due payment yet",
            "next_due": user_plan.next_payment_due
        }, status=400)

    amount = Decimal(user_plan.plan.amount)

    # 💰 WALLET CHECK
    wallet, _ = Wallet.objects.get_or_create(user=user)

    available_balance = (
        calculate_net_balance_for_user(user)
        + wallet.bonus_balance
    )

    if available_balance < amount:
        return JsonResponse({
            "error": "Insufficient wallet balance",
            "required": float(amount),
            "available": float(available_balance),
        }, status=400)

    # 🔥 DEDUCT MONEY
    debit_wallet(
        wallet=wallet,
        amount=amount,
        tx_type="committee_investment",
        source="system",
        reference_id=f"committee_due_{user_plan.id}",
        note=f"Committee due payment"
    )

    # 🔁 UPDATE USER COMMITTEE TOTAL
    uc = user_plan.user_committee
    uc.total_invested += amount
    uc.save(update_fields=["total_invested"])

    # 🔁 UPDATE NEXT DUE DATE
    user_plan.last_payment_at = now()
    user_plan.next_payment_due = now() + timedelta(
        days=user_plan.plan.interval_days
    )
    user_plan.save(update_fields=["last_payment_at", "next_payment_due"])

    return JsonResponse({
        "success": True,
        "message": "Payment successful",
        "amount_paid": float(amount),
        "next_due": user_plan.next_payment_due,
    })




from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UserCommittee


@csrf_exempt
def my_committees(request):
    jwt_authenticator = JWTAuthentication()
    auth_result = jwt_authenticator.authenticate(request)

    if auth_result is None:
        return JsonResponse({"error": "Authentication required"}, status=401)

    user, token = auth_result

    user_committees = UserCommittee.objects.filter(user=user)

    data = []
    for uc in user_committees:
        data.append({
            "id": uc.id,
            "committee_id": uc.committee.id,
            "committee_name": uc.committee.name,
            "joined_at": uc.joined_at,
            "is_active": uc.is_active,
            "total_invested": float(uc.total_invested),
        })

    return JsonResponse({
        "count": user_committees.count(),
        "committees": data,
    })




from django.db.models import Sum
from wallet.models import PaymentMethod, PaymentTransaction
from .models import UserCommittee

from django.http import JsonResponse
from django.db.models import Sum
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view
from wallet.models import PaymentMethod, PaymentTransaction
from .models import UserCommittee


from django.http import JsonResponse
from django.db.models import Sum
from rest_framework.decorators import api_view
from rest_framework_simplejwt.authentication import JWTAuthentication

from wallet.models import PaymentMethod, PaymentTransaction,WalletTransaction
from committees.models import UserCommittee


@api_view(["GET"])
def committee_detail(request, user_committee_id):
    # 🔐 JWT AUTH
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    # 🎯 USER COMMITTEE
    try:
        uc = UserCommittee.objects.get(id=user_committee_id, user=user)
    except UserCommittee.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    # ===============================
    # 💰 FINANCIAL CALCULATIONS
    # ===============================

    # ✅ Total invested (approved only)
    total_invested = abs(
        WalletTransaction.objects.filter(
        wallet=user.wallet,
        tx_type="committee_investment",
        status="success",
    ).aggregate(total=Sum("amount"))["total"] or 0
)

    # ✅ Total withdrawn (approved only)
    total_withdrawn = PaymentTransaction.objects.filter(
        user_committee=uc,
        transaction_type="withdrawal",
        status="approved"
    ).aggregate(total=Sum("amount"))["total"] or 0

    # ✅ Net invested
    net_invested = total_invested - total_withdrawn

    # ✅ ROI on NET invested
    roi_amount = net_invested * (uc.committee.roi_percent / 100)

    # ✅ Final amount after 1 year
    total_after_year = net_invested + roi_amount

    # ===============================
    # 💳 PAYMENT METHODS
    # ===============================
    payment_methods = PaymentMethod.objects.filter(
        is_active=True,
        for_investment=True
    )

    # ===============================
    # 🔔 PAYMENT STATUS MESSAGES
    # ===============================
    payments = PaymentTransaction.objects.filter(
        user_committee=uc
    ).order_by("-created_at")

    payment_messages = []
    for p in payments:
        if p.status in ["approved", "rejected"]:
            payment_messages.append({
                "id": p.id,
                "status": p.status,
                "message": p.admin_message,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            })

    # ===============================
    # ✅ FINAL RESPONSE
    # ===============================
    return JsonResponse({
        "committee_id": uc.committee.id,
        "committee_name": uc.committee.name,

        # 🔥 CORRECT VALUES
        "invested": float(net_invested),
        "withdrawn": float(total_withdrawn),
        "expected_after_year": float(total_after_year),

        "payment_methods": [
            {
                "id": pm.id,
                "name": pm.name,
                "type": pm.method_type,
                "details": {
                    "upi": pm.upi_id,
                    "bank": pm.bank_name,
                    "account": pm.account_number,
                    "ifsc": pm.ifsc_code,
                    "usdt": pm.usdt_address,
                }
            }
            for pm in payment_methods
        ],

        "payment_messages": payment_messages,
    })




from committees.models import CommitteePaymentPlan

def committee_plans(request, committee_id):
    plans = CommitteePaymentPlan.objects.filter(
        committee_id=committee_id,
        is_active=True,
        plan__is_active=True
    ).select_related("plan")

    return JsonResponse([
        {
            "id": cp.plan.id,
            "name": cp.plan.name,
            "type": cp.plan.plan_type,
            "amount": float(cp.plan.amount),
            "interval_days": cp.plan.interval_days,
        }
        for cp in plans
    ], safe=False)



from .models import *

from django.utils.timezone import now
from datetime import timedelta
from rest_framework.decorators import api_view
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import JsonResponse
from .models import UserCommittee, PaymentPlan, UserCommitteePlan

@api_view(["POST"])
def subscribe_plan(request):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)
    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth
    user_committee_id = request.data.get("user_committee_id")
    plan_id = request.data.get("plan_id")

    try:
        uc = UserCommittee.objects.get(id=user_committee_id, user=user)
    except UserCommittee.DoesNotExist:
        return JsonResponse({"error": "Invalid committee"}, status=404)

    # 🔒 HARD CHECK (ONE-TO-ONE SAFETY)
    existing_plan = UserCommitteePlan.objects.filter(
        user_committee=uc
    ).first()

    if existing_plan:
        return JsonResponse(
            {"error": "Plan already subscribed"},
            status=400
        )

    plan = PaymentPlan.objects.get(id=plan_id)

    UserCommitteePlan.objects.create(
        user_committee=uc,
        plan=plan,
        next_payment_due=now() + timedelta(days=plan.interval_days),
        is_active=True
    )

    return JsonResponse({"success": True})




def pending_payments(request, user_committee_id):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)
    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    try:
        plan = UserCommitteePlan.objects.get(
            user_committee_id=user_committee_id,
            is_active=True
        )
    except UserCommitteePlan.DoesNotExist:
        return JsonResponse({
            "has_plan": False
        })

    # user HAS a plan
    if plan.next_payment_due <= now():
        return JsonResponse({
            "has_plan": True,
            "due": True,
            "amount": float(plan.plan.amount),
            "plan_type": plan.plan.plan_type,
            "due_at": plan.next_payment_due.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({
        "has_plan": True,
        "due": False,
        "next_due": plan.next_payment_due.strftime("%Y-%m-%d %H:%M"),
    })


@api_view(["GET"])
def my_due_payments(request):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    plans = UserCommitteePlan.objects.filter(
        user_committee__user=user,
        is_active=True
    )

    due_list = []

    for plan in plans:
        if plan.next_payment_due <= now():
            due_list.append({
                "user_committee_id": plan.user_committee.id,
                "committee_name": plan.user_committee.committee.name,
                "amount": float(plan.plan.amount),
                "plan_type": plan.plan.plan_type,
                "due_at": plan.next_payment_due.strftime("%Y-%m-%d %H:%M"),
            })

    return JsonResponse({
        "has_due": len(due_list) > 0,
        "dues": due_list
    })
