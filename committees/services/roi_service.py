from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from wallet.services import credit_wallet
#def get_total_investment(user_committee):
#    return (
#        user_committee.investment_set
#        .aggregate(total=Sum("amount"))
#        .get("total") or 0
#    )


def calculate_roi_amount(total_investment, roi_percent):
    return (total_investment * roi_percent) / 100


def roi_unlock_date(joined_at):
    return joined_at + timedelta(days=365)


def can_withdraw_roi(user_committee):
    return timezone.now() >= user_committee.roi_unlock_date




from decimal import Decimal

def calculate_total_return(user_committee):
    """
    ROI based on what the USER has actually invested,
    not on committee preset amounts.
    """

    total_invested = user_committee.total_invested or Decimal("0")
    roi_percent = user_committee.committee.roi_percent or Decimal("0")

    roi_amount = total_invested * (roi_percent / Decimal(100))
    total_return = total_invested + roi_amount

    return {
        "roi": round(roi_amount, 2),
        "total_return": round(total_return, 2),
    }


def calculate_committee_return(committee):
    if not committee.yearly_amount:
        return {
            "total_invested": Decimal("0"),
            "roi_amount": Decimal("0"),
            "total_return": Decimal("0"),
        }

    total_invested = committee.yearly_amount
    roi_amount = total_invested * (committee.roi_percent / Decimal(100))
    total_return = total_invested + roi_amount

    return {
        "total_invested": round(total_invested, 2),
        "roi_amount": round(roi_amount, 2),
        "total_return": round(total_return, 2),
    }


def credit_roi_if_eligible(user_committee):
    """
    Credits ROI to wallet ONCE after unlock date
    """

    # 🔒 Already credited
    if user_committee.roi_earned > 0:
        return None

    # 🔒 Not unlocked yet
    if timezone.now() < user_committee.roi_unlock_date:
        return None

    total_invested = user_committee.total_invested or Decimal("0")
    roi_percent = user_committee.committee.roi_percent or Decimal("0")

    if total_invested <= 0 or roi_percent <= 0:
        return None

    roi_amount = (total_invested * roi_percent) / Decimal("100")

    wallet = user_committee.user.wallet

    # 💰 CREDIT WALLET (SOURCE OF TRUTH)
    credit_wallet(
        wallet=wallet,
        amount=roi_amount,
        tx_type="earned",
        source="system",
        reference_id=f"committee_roi_{user_committee.id}",
        note=f"ROI credited for committee {user_committee.committee.name}",
    )

    # 🧠 SYNC BUSINESS STATE
    user_committee.roi_earned = roi_amount
    user_committee.save(update_fields=["roi_earned"])

    return roi_amount