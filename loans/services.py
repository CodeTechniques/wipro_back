from decimal import Decimal
from django.utils.timezone import now
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .models import *
from committees.models import UserCommittee
from notifications.models import Notification


def check_loan_eligibility(user):
    six_months_ago = now() - timedelta(days=180)

    return UserCommittee.objects.filter(
        user=user,
        is_active=True,
        joined_at__lte=six_months_ago
    ).exists()



def approve_loan(application_id, interest_percent, emi_interval):
    """
    Admin-only service to approve a loan application
    """

    application = LoanApplication.objects.get(id=application_id)

    if application.status != "pending":
        raise ValueError("Loan application already processed")

    # Calculate loan values
    interest, total, emi_amount, total_emis = calculate_loan(
        principal=application.requested_amount,
        interest_percent=interest_percent,
        duration_months=application.requested_duration_months,
        emi_interval=emi_interval
    )

    # Create Loan
    loan = Loan.objects.create(
        user=application.user,
        committee=application.committee,
        principal_amount=application.requested_amount,
        interest_percent=interest_percent,
        duration_months=application.requested_duration_months,
        emi_interval_months=emi_interval,
        total_interest=interest,
        total_payable=total,
        emi_amount=emi_amount,
        status="active"
    )

    # Generate EMI dues
    due_date = now().date()

    for _ in range(int(total_emis)):
        due_date += relativedelta(months=emi_interval)

        LoanDue.objects.create(
            loan=loan,
            due_amount=emi_amount,
            due_date=due_date,
            status="pending"
        )

    # Update application
    application.status = "approved"
    application.save()

    # Notify user
    Notification.objects.create(
        user=application.user,
        title="Loan Approved",
        message=f"Your loan of ₹{application.requested_amount} has been approved."
    )

    return loan
