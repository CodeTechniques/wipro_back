from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.authentication import TokenAuthentication
from django.http import JsonResponse
import json

# Create your views here.
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import WalletTransaction, PaymentTransaction
from .serializers import WalletSerializer, WalletTransactionSerializer




class MyWalletTransactionsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WalletTransactionSerializer

    def get_queryset(self):
        return WalletTransaction.objects.filter(wallet=self.request.user.wallet)



from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from decimal import Decimal
from django.contrib.auth.models import User
from .services import credit_wallet, debit_wallet


class AdminWalletAdjustView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        user_id = request.data.get("user_id")
        amount = Decimal(request.data.get("amount"))
        action = request.data.get("action")  # credit / debit
        note = request.data.get("note", "Admin adjustment")

        user = User.objects.get(id=user_id)
        wallet = user.wallet

        if action == "credit":
            credit_wallet(
                wallet=wallet,
                amount=amount,
                tx_type="admin_adjustment",
                source="admin",
                note=note,
            )
        elif action == "debit":
            debit_wallet(
                wallet=wallet,
                amount=amount,
                tx_type="admin_adjustment",
                source="admin",
                note=note,
            )
        else:
            return Response({"error": "Invalid action"}, status=400)

        return Response({"message": "Wallet updated successfully"})
    





from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from wallet.models import Wallet


class WalletDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)

        return Response({
            "balance": str(wallet.balance),
            "status": wallet.status,
        })







from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.timezone import now
import json

from wallet.models import PaymentTransaction, PaymentMethod


# @csrf_exempt
# @require_POST
# def create_payment_request(request):
#     from rest_framework_simplejwt.authentication import JWTAuthentication
#     jwt_authenticator = JWTAuthentication()
#     auth = jwt_authenticator.authenticate(request)

#     if not auth:
#         return JsonResponse({"error": "Unauthorized"}, status=401)

#     user, _ = auth
#     data = json.loads(request.body)
#     screenshot = request.FILES.get("payment_screenshot")

#     tx = PaymentTransaction.objects.create(
#         user=user,
#         user_committee_id=data["user_committee_id"],
#         payment_method_id=data["payment_method_id"],
#         transaction_type="investment",
#         payment_screenshot=screenshot,  # ✅
#     )

#     return JsonResponse({
#         "id": tx.id,
#         "status": tx.status,
#     })


# 

@csrf_exempt
@require_POST
def create_payment_request(request):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    user_committee_id = request.POST.get("user_committee_id")
    payment_method_id = request.POST.get("payment_method_id")
    amount = request.POST.get("amount")  # ✅ FIX
    payment_screenshot = request.FILES.get("payment_screenshot")

    if not payment_method_id:
        return JsonResponse({"error": "payment_method_id required"}, status=400)

    if not amount:
        return JsonResponse({"error": "amount required"}, status=400)

    tx = PaymentTransaction.objects.create(
        user=user,
        user_committee_id=user_committee_id,
        payment_method_id=payment_method_id,
        transaction_type="investment",
        amount=amount,                 # ✅ FIX
        payment_screenshot=payment_screenshot,
        status="pending",
    )

    return JsonResponse({
        "id": str(tx.id),
        "amount": float(tx.amount),
        "status": tx.status,
    })


from django.http import JsonResponse
from .models import PaymentTransaction

def payment_status(request, pk):
    tx = PaymentTransaction.objects.get(pk=pk, user=request.user)

    return JsonResponse({
        "status": tx.status,
        "amount": float(tx.amount or 0),
        "admin_note": tx.admin_note,
    })
from django.http import JsonResponse
from .models import PaymentTransaction

def payment_status(request, pk):
    tx = PaymentTransaction.objects.get(pk=pk, user=request.user)

    return JsonResponse({
        "status": tx.status,
        "amount": float(tx.amount or 0),
        "admin_note": tx.admin_note,
    })




from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view
from wallet.models import *


from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework.decorators import api_view
from rest_framework_simplejwt.authentication import JWTAuthentication
from wallet.models import PaymentTransaction
from committees.models import UserCommittee


@api_view(["GET"])
def payment_history(request, user_committee_id):
    # 🔐 JWT AUTH
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    # 🔎 Validate UserCommittee ownership
    try:
        user_committee = UserCommittee.objects.get(
            id=user_committee_id,
            user=user
        )
    except UserCommittee.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    # ⏰ AUTO-MARK OVERDUE PAYMENTS (CRITICAL)
    PaymentTransaction.objects.filter(
        user_committee=user_committee,
        status="pending",
        due_at__isnull=False,
        due_at__lt=now()
    ).update(status="overdue")

    # 📜 FETCH PAYMENT HISTORY
    payments = PaymentTransaction.objects.filter(
        user_committee=user_committee
    ).select_related("payment_method").order_by("-created_at")

    data = []
    for p in payments:
        data.append({
            "id": p.id,
            "amount": float(p.amount) if p.amount else 0,
            "payment_method": p.payment_method.name if p.payment_method else None,
            "transaction_type": p.transaction_type,
            "status": p.status,  # pending | approved | rejected | overdue
            "reference_id": p.reference_id,
            "admin_message": p.admin_message,
            "due_at": p.due_at.strftime("%Y-%m-%d %H:%M") if p.due_at else None,
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse(data, safe=False)





from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework.decorators import api_view
from rest_framework_simplejwt.authentication import JWTAuthentication
from wallet.models import PaymentTransaction


# @api_view(["GET"])
# def payment_history(request):
#     # 🔐 JWT AUTH
#     jwt_authenticator = JWTAuthentication()
#     auth = jwt_authenticator.authenticate(request)

#     if not auth:
#         return JsonResponse({"error": "Unauthorized"}, status=401)

#     user, _ = auth

#     # ⏰ AUTO-MARK OVERDUE PAYMENTS (USER-WIDE)
#     PaymentTransaction.objects.filter(
#         user=user,
#         status="pending",
#         due_at__isnull=False,
#         due_at__lt=now()
#     ).update(status="overdue")

#     # 📜 FETCH ALL PAYMENT HISTORY FOR USER
#     payments = (
#         PaymentTransaction.objects
#         .filter(user=user)
#         .select_related("payment_method")
#         .order_by("-created_at")
#     )

#     data = []
#     for p in payments:
#         data.append({
#             "id": str(p.id),
#             "amount": float(p.amount) if p.amount is not None else 0,
#             "payment_method": p.payment_method.name if p.payment_method else None,
#             "context": p.context,  # committee | loan_emi | wallet
#             "status": p.status,
#             "admin_message": p.admin_message,
#             "due_at": p.due_at.strftime("%Y-%m-%d %H:%M") if p.due_at else None,
#             "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
#         })

#     return JsonResponse(data, safe=False)



from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now

class MyPendingPaymentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = PaymentTransaction.objects.filter(
            user=request.user,
            status="pending"
        ).order_by("due_at", "created_at")

        data = []
        for p in payments:
            data.append({
                "id": p.id,
                "context": p.context,
                "amount": float(p.amount),
                "due_at": p.due_at,
                "admin_message": p.admin_message,
            })

        return Response(data)






from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import PaymentMethod


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_methods(request):
    methods = PaymentMethod.objects.filter(is_active=True)

    data = []
    for m in methods:
        data.append({
            "id": m.id,
            "name": m.name,
            "method_type": m.method_type,
            "upi_id": m.upi_id,
            "bank_name": m.bank_name,
            "account_holder": m.account_holder,
            "account_number": m.account_number,
            "ifsc_code": m.ifsc_code,
            "usdt_address": m.usdt_address,
        })

    return Response(data)





from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import PaymentRequest, PaymentMethod

# class CreatePaymentRequestView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         amount = request.data.get("amount")
#         purpose = request.data.get("purpose")
#         payment_method_id = request.data.get("payment_method_id")

#         if not amount or not purpose or not payment_method_id:
#             return Response(
#                 {"error": "amount, purpose and payment_method_id required"},
#                 status=400
#             )

#         payment_method = PaymentMethod.objects.get(id=payment_method_id)

#         pr = PaymentRequest.objects.create(
#             user=request.user,
#             amount=amount,
#             purpose=purpose,
#             payment_method=payment_method
#         )

#         return Response({
#             "id": pr.id,
#             "status": pr.status,
#             "message": "Payment request created"
#         })

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from wallet.models import PaymentRequest, PaymentMethod


class CreatePaymentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get("amount")
        request_type = request.data.get("request_type")  # deposit / withdraw
        payment_method_id = request.data.get("payment_method_id")
        payment_screenshot = request.FILES.get("payment_screenshot")
        user_payment_method_details = request.data.get(
            "withdrawal_details"
        )  # 👈 from frontend

        if not amount or not request_type:
            return Response(
                {"error": "amount and request_type are required"},
                status=400
            )

        if request_type not in ["deposit", "withdraw"]:
            return Response(
                {"error": "Invalid request_type"},
                status=400
            )
        
        if request_type == "withdraw" and not user_payment_method_details:
            return Response(
                {"error": "User payment method details required for withdrawal"},
                status=400
            )

        payment_method = None
        if payment_method_id:
            payment_method = PaymentMethod.objects.get(id=payment_method_id)

        pr = PaymentRequest.objects.create(
            user=request.user,
            amount=amount,
            request_type=request_type,
            payment_method=payment_method,
            payment_screenshot=payment_screenshot,  # ✅ SAVED
            user_payment_method_details=user_payment_method_details,
        )

        return Response({
            "id": pr.id,
            "status": pr.status,
            "message": "Payment request created"
        })





# class MyPaymentHistoryView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         payments = PaymentRequest.objects.filter(user=request.user).order_by("-created_at")

#         data = []
#         for p in payments:
#             data.append({
#                 "id": p.id,
#                 "amount": float(p.amount),
#                 "purpose": p.purpose,
#                 "status": p.status,
#                 "payment_method": p.payment_method.name if p.payment_method else None,
#                 "admin_message": p.admin_message,
#                 "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
#             })

#         return Response(data)




class MyPaymentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = PaymentRequest.objects.filter(
            user=request.user
        ).order_by("-created_at")

        data = []
        for p in payments:
            data.append({
                "id": p.id,
                "amount": float(p.amount),
                "request_type": p.request_type,  # ✅ NEW
                "status": p.status,
                "payment_method": p.payment_method.name if p.payment_method else None,
                "admin_message": p.admin_message,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        return Response(data)



# wallet/views.py
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_detail(request, pk):
    try:
        tx = PaymentTransaction.objects.get(id=pk, user=request.user)
    except PaymentTransaction.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    return Response({
        "amount": float(tx.amount),
        "context": tx.context,
        "reference_id": tx.reference_id,
    })



# wallet/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from wallet.models import *

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def wallet_payment_transactions(request):
#     payments = PaymentTransaction.objects.filter(
#         user=request.user,
#         status="approved",
#         transaction_type__in=["investment", "withdrawal"]
#     ).order_by("-created_at")

#     payments = (
#         PaymentRequest.objects
#         .filter(user=user, status="approved")
#         .select_related("payment_method")
#         .order_by("-created_at")
#     )

#     data = []

#     for p in payments:
#         # classify earn vs paid
#         if p.purpose in ["investment", "wallet topup"]:
#             tx_type = "earn"
#             amount = float(p.amount)
#         else:
#             tx_type = "paid"
#             amount = -float(p.amount)


#     for p in payments:
#         data.append({
#             "id": p.id,
#             "type": p.transaction_type,  # investment / withdrawal
#             "payment_method": p.payment_method.name if p.payment_method else "-",
#             "tx_type": tx_type, 
#             "amount": float(p.amount),
#             "created_at": p.created_at.strftime("%Y-%m-%d"),
#         })

#     return Response(data)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from wallet.models import PaymentRequest


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def wallet_payment_transactions(request):
#     user = request.user

#     payments = (
#         PaymentRequest.objects
#         .filter(user=user, status="approved")
#         .select_related("payment_method")
#         .order_by("-created_at")
#     )

#     data = []

#     for p in payments:
#         if p.earned > 0:
#             data.append({
#                 "id": p.id,
#                 "tx_type": "earn",
#                 "payment_method": p.payment_method.name if p.payment_method else "-",
#                 "amount": float(p.earned),
#                 "created_at": p.created_at.strftime("%Y-%m-%d"),
#             })

#         if p.paid > 0:
#             data.append({
#                 "id": f"{p.id}-paid",
#                 "tx_type": "paid",
#                 "payment_method": p.payment_method.name if p.payment_method else "-",
#                 "amount": float(p.paid),
#                 "created_at": p.created_at.strftime("%Y-%m-%d"),
#             })

#     return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_payment_transactions(request):
    user = request.user

    payments = (
        PaymentRequest.objects
        .filter(user=user, status="approved")
        .select_related("payment_method")
        .order_by("-created_at")
    )

    data = []

    for p in payments:
        if p.request_type == "deposit":
            data.append({
                "id": p.id,
                "tx_type": "earn",
                "payment_method": p.payment_method.name if p.payment_method else "-",
                "amount": float(p.earned),
                "created_at": p.created_at.strftime("%Y-%m-%d"),
            })

        elif p.request_type == "withdraw":
            data.append({
                "id": p.id,
                "tx_type": "paid",
                "payment_method": p.payment_method.name if p.payment_method else "-",
                "amount": float(p.paid),
                "created_at": p.created_at.strftime("%Y-%m-%d"),
            })

    return Response(data)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_summary(request):
    payments = PaymentTransaction.objects.filter(
        user=request.user,
        status="approved"
    )

    total_invested = sum(
        p.amount for p in payments if p.transaction_type == "investment"
    )

    total_withdrawn = sum(
        p.amount for p in payments if p.transaction_type == "withdrawal"
    )

    balance = total_invested - total_withdrawn

    return Response({
        "balance": float(balance),
        "total_deposit": float(total_invested),
        "total_withdraw": float(total_withdrawn),
    })






from wallet.calculations import *
from wallet.models import Wallet


class MyWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # ensure wallet exists
        wallet, _ = Wallet.objects.get_or_create(user=user)
            
        return Response({
            "total_invested": float(
                calculate_total_investment_for_user(user)
            ),
            "total_withdrawn": float(
                calculate_total_withdrawal_for_user(user)
            ),
            "total_earned": float(
                calculate_total_earned_for_user(user)
            ),
            "total_paid": float(
                calculate_total_paid_for_user(user)
            ),
            "net_balance": float(
                calculate_net_balance_for_user(user)
            ),

            "bonus_balance": float(wallet.bonus_balance),  # 👈 NEW
            
            "status": wallet.status,
            "updated_at": wallet.updated_at.strftime("%Y-%m-%d %H:%M"),
        })
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.utils import timezone

from .models import PaymentTransaction, PaymentMethod, Wallet
from committees.models import UserCommittee


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone

from wallet.models import Wallet, PaymentTransaction, PaymentMethod
from committees.models import UserCommittee


def get_available_balance(wallet):
    """
    Calculates REAL available balance from approved transactions
    """
    credited = PaymentTransaction.objects.filter(
        wallet=wallet,
        status="approved",
        wallet_effect="credit"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    debited = PaymentTransaction.objects.filter(
        wallet=wallet,
        status="approved",
        wallet_effect="debit"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return credited - debited + wallet.bonus_balance


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw_request(request):
    user = request.user

    # ---------------------------
    # 🔹 INPUT VALIDATION
    # ---------------------------
    try:
        amount = Decimal(request.data.get("amount"))
    except:
        return Response({"error": "Invalid amount"}, status=400)

    if amount <= 0:
        return Response({"error": "Amount must be greater than zero"}, status=400)

    method_id = request.data.get("payment_method_id")
    withdrawal_details = request.data.get("withdrawal_details", "")
    user_committee_id = request.data.get("user_committee_id")
    payment_screenshot = request.FILES.get("payment_screenshot")

    # ---------------------------
    # 🔹 WALLET CHECK
    # ---------------------------
    try:
        wallet = Wallet.objects.get(user=user)
    except Wallet.DoesNotExist:
        return Response({"error": "Wallet not found"}, status=404)

    available_balance = get_available_balance(wallet)

    # if available_balance < amount:
    #     return Response(
    #         {
    #             "error": "Insufficient balance",
    #             "available_balance": float(available_balance),
    #         },
    #         status=400,
    #     )

    # ---------------------------
    # 🔹 PAYMENT METHOD CHECK
    # ---------------------------
    try:
        payment_method = PaymentMethod.objects.get(
            id=method_id,
            is_active=True,
            for_withdrawal=True
        )
    except PaymentMethod.DoesNotExist:
        return Response({"error": "Invalid payment method"}, status=400)

    # ---------------------------
    # 🔹 OPTIONAL COMMITTEE
    # ---------------------------
    user_committee = None
    if user_committee_id:
        try:
            user_committee = UserCommittee.objects.get(
                id=user_committee_id,
                user=user
            )
        except UserCommittee.DoesNotExist:
            return Response({"error": "Invalid committee"}, status=400)

    # ---------------------------
    # 🔹 CREATE WITHDRAWAL REQUEST
    # ---------------------------
    PaymentTransaction.objects.create(
        user=user,
        user_committee=user_committee,
        transaction_type="withdrawal",
        amount=amount,
        payment_method=payment_method,
        withdrawal_details=withdrawal_details,
        wallet=wallet,
        wallet_effect="debit",
        payment_screenshot=payment_screenshot,  # ✅ ADD THIS
        status="pending",
        created_at=timezone.now(),
    )

    return Response(
        {
            "success": True,
            "message": "Withdrawal request submitted. Awaiting admin approval.",
            "amount": float(amount),
        },
        status=201,
    )
