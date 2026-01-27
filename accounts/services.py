from django.db.models import Count, Sum
from django.utils.timezone import now, timedelta

from accounts.models import *

def generate_weekly_leaderboard():
    start_date = now() - timedelta(days=7)

    data = (
        ReferralEarning.objects
        .filter(created_at__gte=start_date)
        .values("user")
        .annotate(
            total_referrals=Count("referred_user", distinct=True),
            total_earnings=Sum("amount"),
        )
        .order_by("-total_earnings")
    )

    ReferralLeaderboard.objects.filter(period="weekly").delete()

    for index, item in enumerate(data, start=1):
        ReferralLeaderboard.objects.create(
            user_id=item["user"],
            period="weekly",
            rank=index,
            total_referrals=item["total_referrals"],
            total_earnings=item["total_earnings"] or 0,
        )
