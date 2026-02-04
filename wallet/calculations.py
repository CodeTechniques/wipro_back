from decimal import Decimal
from django.db.models import Sum

from wallet.models import (
    Wallet,
    WalletTransaction,
    PaymentRequest,
)


# ======================================================
# TOTAL INVESTMENT (ALL TIME)
# ======================================================
def calculate_total_investment_for_user(user):
    """
    Total amount invested by user (committee + property etc.)
    Derived from WalletTransaction.
    """
    total = (
        WalletTransaction.objects.filter(
            wallet=user.wallet,
            tx_type__in=["committee_investment"],
            status="success",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # amount is stored negative for debit → return positive number
    return abs(total)


# ======================================================
# TOTAL WITHDRAWAL (ALL TIME)
# ======================================================
def calculate_total_withdrawal_for_user(user):
    """
    Total withdrawn from wallet
    """
    total = (
        WalletTransaction.objects.filter(
            wallet=user.wallet,
            tx_type="withdraw",
            status="success",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    return abs(total)


# ======================================================
# TOTAL EARNED (ALL TIME)
# ======================================================
def calculate_total_earned_for_user(user):
    """
    Total earned via deposits / interest
    """
    total = (
        WalletTransaction.objects.filter(
            wallet=user.wallet,
            amount__gt=0,
            status="success",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    return total


# ======================================================
# TOTAL PAID (ALL TIME)
# ======================================================
def calculate_total_paid_for_user(user):
    """
    Total paid out (all debits)
    """
    total = (
        WalletTransaction.objects.filter(
            wallet=user.wallet,
            amount__lt=0,
            status="success",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    return abs(total)


# ======================================================
# NET BALANCE (SOURCE OF TRUTH)
# ======================================================
def calculate_net_balance_for_user(user):
    """
    FINAL NET BALANCE
    (Do NOT recalculate from transactions anymore)
    """
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet.balance
