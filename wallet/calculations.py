from decimal import Decimal
from django.db.models import Sum
from wallet.models import *


def calculate_total_investment_for_user(user):
    """
    Calculates total investment from APPROVED payment transactions.
    """

    result = (
        PaymentTransaction.objects
        .filter(
            user=user,
            status="approved",
            transaction_type="investment",
            amount__isnull=False,
        )
        .aggregate(total=Sum("amount"))
    )

    return result["total"] or Decimal("0.00")





def calculate_net_balance_for_user(user):
    from django.db.models import Sum
    from wallet.models import PaymentTransaction

    invested = (
        PaymentTransaction.objects
        .filter(user=user, status="approved", transaction_type="investment")
        .aggregate(total=Sum("amount"))["total"] or 0
    )

    withdrawn = (
        PaymentTransaction.objects
        .filter(user=user, status="approved", transaction_type="withdrawal")
        .aggregate(total=Sum("amount"))["total"] or 0
    )

    return invested - withdrawn



def calculate_total_withdrawal_for_user(user):
    return (
        PaymentTransaction.objects
        .filter(
            user=user,
            status="approved",
            transaction_type="withdrawal",
            amount__isnull=False,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )


def calculate_total_earned_for_user(user):
    return (
        PaymentRequest.objects
        .filter(user=user, status="approved")
        .aggregate(total=Sum("earned"))["total"]
        or Decimal("0.00")
    )


def calculate_total_paid_for_user(user):
    return (
        PaymentRequest.objects
        .filter(user=user, status="approved")
        .aggregate(total=Sum("paid"))["total"]
        or Decimal("0.00")
    )


def calculate_net_balance_for_user(user):
    invested = calculate_total_investment_for_user(user)
    withdrawn = calculate_total_withdrawal_for_user(user)
    earned = calculate_total_earned_for_user(user)
    paid = calculate_total_paid_for_user(user)
    return invested - withdrawn + earned - paid