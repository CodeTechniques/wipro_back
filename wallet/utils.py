from accounts.models import UserVerification
from decimal import Decimal
from .calculations import calculate_total_earned_for_user

def get_referred_by_user(user):
    try:
        return user.verification.referred_by
    except UserVerification.DoesNotExist:
        return None


def calculate_referral_commission(user):
    total_earned = calculate_total_earned_for_user(user)
    if not total_earned:
        return Decimal("0.00")

    return (Decimal(total_earned) * Decimal("0.01")).quantize(Decimal("0.01"))
