from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash

from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    ChangePasswordSerializer
)
from django.contrib.auth.models import User
from .models import *

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

class UserLoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Invalid old password'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        
        return Response({'message': 'Password changed successfully'}, 
                       status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import UserVerification
from .serializers import UserVerificationSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.contrib.auth.models import User


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def kyc_view(request):
    user = request.user

    if request.method == "GET":
        kyc = UserVerification.objects.filter(user=user).first()
        if not kyc:
            return Response({"exists": False})

        return Response({
            "exists": True,
            "status": kyc.status,
            "data": UserVerificationSerializer(kyc).data
        })

    if request.method == "POST":
        print("RAW DATA:", request.data)

        kyc = UserVerification.objects.filter(user=user).first()
        data = request.data.copy()

        referral_code = data.get("referral_code")

        # remove fields not in serializer
        data.pop("kyc_type", None)
        data.pop("referral_code", None)

        serializer = UserVerificationSerializer(
            instance=kyc,
            data=data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        # 🔥 HANDLE REFERRAL
        referred_user = None
        if referral_code:
            print(referral_code)
            try:
                ref_obj = UserReferral.objects.get(referral_code=referral_code)
                referred_user = ref_obj.user
            except UserReferral.DoesNotExist:
                return Response({"error": "Invalid referral code"}, status=400)

        serializer.save(
            user=user,
            status="pending",
            referred_by=referred_user   # 🔥 SAVE HERE
        )

        return Response(serializer.data)



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import UserReferral


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_referral_link(request):
    ref, created = UserReferral.objects.get_or_create(
        user=request.user
    )

    return Response({
        "referral_code": ref.referral_code
    })







@api_view(["GET"])
def referral_leaderboard(request):
    period = request.GET.get("period", "weekly")

    leaderboard = ReferralLeaderboard.objects.filter(period=period)

    data = [
        {
            "rank": l.rank,
            "name": l.user.username,
            "referrals": l.total_referrals,
            "amount": l.total_earnings,
        }
        for l in leaderboard
    ]

    return Response(data)






from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UserProfile
from .serializers import ProfileSerializer


class ProfileView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile
    

from django.core.mail import send_mail
from django.utils import timezone
from .models import PasswordResetOTP
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

@api_view(["POST"])
@permission_classes([AllowAny])
def send_reset_otp(request):
    email = request.data.get("email")

    if not email:
        return Response({"error": "Email required"}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist"}, status=404)

    otp = PasswordResetOTP.generate_otp()

    PasswordResetOTP.objects.create(
        user=user,
        email=email,
        otp=otp
    )

    subject = "WipoGroup Password Reset OTP"

    html_content = f"""
<div style="font-family:Arial,Helvetica,sans-serif;background:#f5f6fa;padding:30px">
  <div style="max-width:600px;margin:auto;background:#ffffff;border-radius:12px;padding:40px">

    <h2 style="color:#111;">WipoGroup</h2>

    <p style="font-size:16px;color:#333;">
      Hello, {user.first_name} {user.last_name}
    </p>

    <p style="font-size:16px;color:#333;">
      You requested to reset your password for your WipoGroup account.
    </p>

    <div style="
        margin:30px 0;
        text-align:center;
        font-size:32px;
        letter-spacing:8px;
        font-weight:bold;
        color:#2d7ef7;
        background:#f1f5ff;
        padding:20px;
        border-radius:10px;
    ">
        {otp}
    </div>

    <p style="font-size:15px;color:#555;">
      This OTP is valid for <b>10 minutes</b>.
    </p>

    <p style="font-size:15px;color:#999;">
      If you didn’t request this, you can safely ignore this email.
    </p>

    <hr style="margin:30px 0;border:none;border-top:1px solid #eee"/>

    <p style="font-size:13px;color:#aaa;">
      © {timezone.now().year} WipoGroup. All rights reserved.
        </p>
    
      </div>
    </div>
    """

    msg = EmailMultiAlternatives(
        subject,
        f"Your OTP is {otp}",  # fallback text
        None,
        [email],
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return Response({"message": "OTP sent to email"})



@api_view(["POST"])
@permission_classes([AllowAny])
def verify_reset_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    try:
        record = PasswordResetOTP.objects.filter(
            email=email,
            otp=otp,
            is_verified=False
        ).latest("created_at")
    except PasswordResetOTP.DoesNotExist:
        return Response({"error": "Invalid OTP"}, status=400)

    if record.is_expired():
        return Response({"error": "OTP expired"}, status=400)

    record.is_verified = True
    record.save()

    return Response({"message": "OTP verified"})



@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get("email")
    new_password = request.data.get("new_password")

    try:
        record = PasswordResetOTP.objects.filter(
            email=email,
            is_verified=True
        ).latest("created_at")
    except PasswordResetOTP.DoesNotExist:
        return Response({"error": "OTP not verified"}, status=400)

    user = record.user
    user.set_password(new_password)
    user.save()

    # cleanup
    record.delete()

    return Response({"message": "Password reset successful"})



from django.core.mail import EmailMultiAlternatives
@api_view(["POST"])
@permission_classes([AllowAny])
def contact_us(request):
    full_name = request.data.get("full_name")
    email = request.data.get("email")
    message = request.data.get("message")

    if not full_name or not email or not message:
        return Response({"error": "All fields required"}, status=400)

    company_email = "wipogroupn@gmail.com"

    subject = f"New Contact Message - {full_name}"

    html_content = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;background:#f5f6fa;padding:30px">
      <div style="max-width:650px;margin:auto;background:#ffffff;border-radius:12px;padding:40px">

        <h2 style="color:#111;">WipoGroup</h2>

        <p style="font-size:16px;color:#333;">
          You received a new contact message from your website.
        </p>

        <div style="
            background:#f8f9ff;
            padding:20px;
            border-radius:10px;
            margin:20px 0;
        ">
            <p><b>Name:</b> {full_name}</p>
            <p><b>Email:</b> {email}</p>
        </div>

        <div style="
            background:#fafafa;
            padding:20px;
            border-radius:10px;
            border:1px solid #eee;
        ">
            <p style="white-space:pre-line">{message}</p>
        </div>

        <hr style="margin:30px 0;border:none;border-top:1px solid #eee"/>

        <p style="font-size:13px;color:#aaa;">
          Sent from WipoGroup website contact form
        </p>

        <p style="font-size:12px;color:#aaa;">
          {timezone.now().strftime("%d %b %Y %H:%M")}
        </p>

      </div>
    </div>
    """

    msg = EmailMultiAlternatives(
        subject,
        message,
        None,
        [company_email],
        reply_to=[email],  # so you can reply directly
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return Response({"message": "Message sent successfully"})
