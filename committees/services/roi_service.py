from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

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




from decimal import Decimal

from decimal import Decimal

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
