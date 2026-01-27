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
        print("FILES:", request.FILES)
        kyc, created = UserVerification.objects.get_or_create(user=user)

        # 🔥 READ & REMOVE referral_code BEFORE serializer
        referral_code = request.data.get("referral_code")

        # Make a mutable copy of data
        data = request.data.copy()
        data.pop("referral_code", None)

        # 🔹 Apply referral ONLY ONCE
        if referral_code and not kyc.referred_by:
            ref = UserReferral.objects.filter(
                referral_code=referral_code
            ).select_related("user").first()

            if ref and ref.user != user:
                kyc.referred_by = ref.user
                kyc.save(update_fields=["referred_by"])

        serializer = UserVerificationSerializer(
            kyc,
            data=data,          # 👈 use cleaned data
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(status="pending")

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