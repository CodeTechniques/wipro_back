from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import *

urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='user_register'),
    path('login/', views.UserLoginView.as_view(), name='user_login'),
    path('logout/', views.logout_view, name='user_logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User management
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('change-password/', views.change_password_view, name='change_password'),

    path("kyc/", kyc_view),
    path("my-referral/", my_referral_link),
    path("referral-leaderboard/", referral_leaderboard, name="referral-leaderboard"),
    path("profile-details/", ProfileView.as_view(), name="profile-details"),



    path("forgot-password/send-otp/", views.send_reset_otp,name="forget-password"),
    path("forgot-password/verify-otp/",views.verify_reset_otp,name="varify-otp"),
    path("forgot-password/reset/", views.reset_password,name="reset-password"),
    path("contact-us/", views.contact_us,name="contact_us"),

]
