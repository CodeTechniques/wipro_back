from decimal import Decimal
from django.utils.timezone import now
from wallet.services import credit_wallet, debit_wallet
from .models import Investment


def create_investment(*, user, amount):
    investment = Investment.objects.create(
        user=user,
        amount=amount,
    )

    credit_wallet(
        wallet=user.wallet,
        amount=amount,
        tx_type="investment",
        source="system",
        reference_id=investment.id,
        note="Investment created",
    )

    return investment


from decimal import Decimal
from django.utils.timezone import now

ANNUAL_RATE = Decimal("0.15")
DAYS_IN_YEAR = Decimal("365")


def calculate_accrued_interest(principal: Decimal, start_date):
    """
    Interest accrues from DAY 1.
    Paid only if >= 365 days completed.
    """
    days_invested = Decimal((now() - start_date).days)

    if days_invested < DAYS_IN_YEAR:
        return Decimal("0.00")  # locked interest

    interest = principal * ANNUAL_RATE * (days_invested / DAYS_IN_YEAR)
    return interest.quantize(Decimal("0.01"))



def withdraw_investment(*, investment: Investment):
    if investment.status != "active":
        raise ValueError("Investment already withdrawn")

    principal = investment.amount
    interest = Decimal("0.00")

    if investment.is_interest_unlocked():
        interest = calculate_accrued_interest(
        principal=principal,
        start_date=investment.start_date
    )

    total_payout = principal + interest

    debit_wallet(
        wallet=investment.user.wallet,
        amount=total_payout,
        tx_type="withdrawal",
        source="system",
        reference_id=investment.id,
        note="Investment withdrawal",
    )

    investment.status = "withdrawn"
    investment.withdrawn_at = now()
    investment.save(update_fields=["status", "withdrawn_at"])

    return {
        "principal": principal,
        "interest": interest,
        "total": total_payout,
        "days_invested": (now() - investment.start_date).days
    }
