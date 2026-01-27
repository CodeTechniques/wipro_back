from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import *
from .services import send_notification


class MyNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        return Response([
            {
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "read": n.is_read
            }
            for n in qs
        ])


class AdminSendNotificationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        send_notification(
            user_id=request.data["user_id"],
            title=request.data["title"],
            message=request.data["message"],
            type=request.data.get("type", "info"),
        )
        return Response({"message": "Sent"})




from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Notification

def my_notifications(request):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if auth is None:
        return JsonResponse(
            {"detail": "Authentication required"},
            status=401
        )

    user, token = auth

    notifications = Notification.objects.filter(
        user=user
    ).order_by("-created_at")

    data = []
    for n in notifications:
        data.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse(data, safe=False)






from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.http import require_POST
from .models import DueNotification


def due_notifications(request):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    dues = DueNotification.objects.filter(
        user=user,
        is_active=True
    ).exclude(
    responses__user=user
    ).select_related("user_committee", "committee", "plan")

    data = []

    for d in dues:
        # 🔒 SAFETY CHECK
        if not d.user_committee:
            continue   # skip broken rows

        data.append({
            "id": d.id,
            "amount": float(d.amount),
            "repeat_after_minutes": d.repeat_after_minutes,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
            "committee_name": d.committee.name,
            "plan_name": d.plan.name,
            "user_committee_id": d.user_committee.id,
            "plan_id": d.plan.id,
        })

    return JsonResponse(data, safe=False)


@require_POST
def dismiss_due_notification(request, pk):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    try:
        due = DueNotification.objects.get(
            id=pk,
            user=user,
            is_active=True
        )
        due.is_active = False
        due.save(update_fields=["is_active"])
        return JsonResponse({"success": True})
    except DueNotification.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)





import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import DueNotification, DueResponse

@csrf_exempt
@require_POST
def due_response(request, due_id):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    # 🔍 DEBUG (TEMP)
    print("RAW BODY:", request.body)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        print("JSON ERROR:", e)
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    action = data.get("action")
    print("ACTION RECEIVED:", action)

    if action not in ["pay_now", "pay_later"]:
        return JsonResponse({"error": "Invalid action"}, status=400)

    try:
        due = DueNotification.objects.get(
            id=due_id,
            user=user,
            is_active=True
        )
    except DueNotification.DoesNotExist:
        return JsonResponse({"error": "Due not found"}, status=404)

    DueResponse.objects.create(
        user=user,
        due_notification=due,
        committee=due.committee,
        plan=due.plan,
        action=action,
    )

    return JsonResponse({"success": True})




@csrf_exempt
@require_POST
def mark_notification_read(request, pk):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    Notification.objects.filter(
        id=pk,
        user=user
    ).update(is_read=True)

    return JsonResponse({"success": True})




from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from committees.models import UserCommittee
from .models import CommitteePaymentDue, DueNotification


def committee_dues(request):
    """
    Returns committee-wide dues relevant to logged-in user
    """
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    committees = UserCommittee.objects.filter(
        user=user,
        is_active=True
    ).values_list("committee_id", flat=True)

    dues = CommitteePaymentDue.objects.filter(
        committee_id__in=committees,
        is_active=True
    ).select_related("committee", "plan")

    data = []
    for d in dues:
        data.append({
            "id": d.id,
            "committee_id": d.committee.id,
            "committee_name": d.committee.name,
            "plan_id": d.plan.id,
            "plan_name": d.plan.name,
            "amount": float(d.amount),
            "repeat_after_minutes": d.repeat_after_minutes,
        })

    return JsonResponse(data, safe=False)






@csrf_exempt
@require_POST
def expand_committee_due(request, due_id):
    """
    Creates DueNotification for THIS USER only
    (called when user sees the message)
    """
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    try:
        due = CommitteePaymentDue.objects.get(
            id=due_id,
            is_active=True
        )
    except CommitteePaymentDue.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    # Prevent duplicates
    exists = DueNotification.objects.filter(
        user=user,
        committee=due.committee,
        plan=due.plan,
        is_active=True
    ).exists()

    if exists:
        return JsonResponse({"already_exists": True})

    DueNotification.objects.create(
        user=user,
        committee=due.committee,
        plan=due.plan,
        amount=due.amount,
        repeat_after_minutes=due.repeat_after_minutes,
        is_active=True,
    )

    return JsonResponse({"success": True})






from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.authentication import JWTAuthentication
from committees.models import UserCommittee
from .models import CommitteePaymentDue, DueNotification, DueResponse


import json

@csrf_exempt
@require_POST
def committee_due_response(request, due_id):
    jwt_authenticator = JWTAuthentication()
    auth = jwt_authenticator.authenticate(request)

    if not auth:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user, _ = auth

    try:
        data = json.loads(request.body.decode("utf-8"))
        action = data.get("action")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if action not in ["pay_now", "pay_later"]:
        return JsonResponse({"error": "Invalid action"}, status=400)

    try:
        committee_due = CommitteePaymentDue.objects.get(
            id=due_id,
            is_active=True
        )
    except CommitteePaymentDue.DoesNotExist:
        return JsonResponse({"error": "Committee due not found"}, status=404)

    try:
        uc = UserCommittee.objects.get(
            user=user,
            committee=committee_due.committee,
            is_active=True
        )
    except UserCommittee.DoesNotExist:
        return JsonResponse({"error": "User not in committee"}, status=400)

    due, _ = DueNotification.objects.get_or_create(
        user=user,
        committee=committee_due.committee,
        plan=committee_due.plan,
        defaults={
            "amount": committee_due.amount,
            "repeat_after_minutes": committee_due.repeat_after_minutes,
            "is_active": True,
        }
    )

    DueResponse.objects.create(
        user=user,
        due_notification=due,
        committee=committee_due.committee,
        plan=committee_due.plan,
        action=action,
    )

    return JsonResponse({
        "success": True,
        "user_committee_id": uc.id,
        "plan_id": committee_due.plan.id,
    })








from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import UniversalDue


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def universal_dues(request):
    dues = (
        UniversalDue.objects
        .filter(user=request.user, is_active=True, is_resolved=False)
        .exclude(responses__user=request.user)
        .order_by("-created_at")
    )

    return Response([
        {
            "id": d.id,
            "heading": d.heading,
            "description": d.description,
            "amount": d.amount,
            "context": d.context,
            "reference_id": d.reference_id,
        }
        for d in dues
    ])










from .models import UniversalDue, UniversalDueResponse


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def universal_due_response(request, due_id):
    action = request.data.get("action")

    if action not in ["pay_now", "pay_later"]:
        return Response({"error": "Invalid action"}, status=400)

    due = UniversalDue.objects.get(
        id=due_id,
        user=request.user,
        is_active=True,
        is_resolved=False
    )

    UniversalDueResponse.objects.create(
        user=request.user,
        due=due,
        action=action
    )

    if action == "pay_later":
        return Response({"success": True})

    # Pay now → frontend will redirect to payment page
    return Response({
        "success": True,
        "amount": due.amount,
        "context": due.context,
        "reference_id": due.reference_id,
    })
