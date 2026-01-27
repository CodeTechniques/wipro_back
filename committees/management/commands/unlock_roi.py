from django.core.management.base import BaseCommand
from committees.models import UserCommittee
from committees.services.roi_service import (
    get_total_investment,
    calculate_roi_amount,
    can_withdraw_roi
)

class Command(BaseCommand):
    help = "Unlock ROI after 1 year"

    def handle(self, *args, **kwargs):
        for uc in UserCommittee.objects.filter(is_active=True):
            if can_withdraw_roi(uc) and uc.roi_earned == 0:
                total = get_total_investment(uc)
                uc.roi_earned = calculate_roi_amount(
                    total,
                    uc.committee.roi_percent
                )
                uc.save()

        self.stdout.write("ROI unlock process completed.")
