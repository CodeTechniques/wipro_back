from decimal import Decimal

def get_committee_join_amount(committee):
    """
    Priority:
    daily > monthly > yearly
    """
    if committee.daily_amount:
        return committee.daily_amount, "daily"
    if committee.monthly_amount:
        return committee.monthly_amount, "monthly"
    if committee.yearly_amount:
        return committee.yearly_amount, "yearly"
    return Decimal("0"), None
