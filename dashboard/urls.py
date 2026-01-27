from django.urls import path
from .views import *

urlpatterns = [
    path("wallet/", DashboardWalletView.as_view()),
    path("investments/", DashboardInvestmentView.as_view()),
    path("loans/", DashboardLoanView.as_view()),
    path("notifications/", DashboardNotificationView.as_view()),
]
