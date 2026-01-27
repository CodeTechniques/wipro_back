from django.urls import path
from .views import MyWalletView, MyWalletTransactionsView, AdminWalletAdjustView
from .views import *
from . import views
urlpatterns = [
    path("me/", MyWalletView.as_view()),
    path("transactions/", MyWalletTransactionsView.as_view()),
    path("admin/adjust/", AdminWalletAdjustView.as_view()),
    path(
        "payment-request/",
        create_payment_request,
        name="payment-request"
    ),
    path("payment-status/<int:pk>/", payment_status),
    path("payment-history/<int:user_committee_id>/", payment_history),
    path("pending", MyPendingPaymentsView.as_view(), name="pending-payments"),
    path("payment-methods/", payment_methods),   # ✅ ADD THIS

    path("payment-history/", MyPaymentHistoryView.as_view()),
    path("all-payment-request/", CreatePaymentRequestView.as_view()),
    # wallet/urls.py
path("payments/<uuid:pk>/", payment_detail),
path("wallet-payments/", wallet_payment_transactions),

path(
        "withdraw-request/",
        views.withdraw_request,
        name="withdraw-request"
    ),

]
