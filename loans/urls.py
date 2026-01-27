from django.urls import path
from .views import *

urlpatterns = [
    path("eligibility/", LoanEligibilityView.as_view()),
    path("apply/", ApplyLoanView.as_view()),
    path("approve/<uuid:loan_id>/", ApproveLoanView.as_view()),
    path("my-loans/", MyLoansView.as_view(), name="my-loans"),
    path("my-applications/", MyLoanApplicationView.as_view(), name="my-loan-applications"),
    path("wallet/", LoanWalletView.as_view(), name="loan-wallet"),
    path("dashboard/", LoanEligibilityDashboardView.as_view()),
    path("dashboard-data/", LoanDashboardDataView.as_view()),
    path("user-loan/", UserLoanDetailView.as_view()),
    path("emis/", LoanEmiListView.as_view()),
    


]
