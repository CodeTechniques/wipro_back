from django.core.management.base import BaseCommand
from committees.models import UserCommittee
from committees.services.roi_service import credit_roi_if_eligible

class Command(BaseCommand):
    help = "Credit ROI to eligible committee users"

    def handle(self, *args, **kwargs):
        qs = UserCommittee.objects.select_related(
            "user", "committee", "user__wallet"
        )

        credited = 0

        for uc in qs:
            if credit_roi_if_eligible(uc):
                credited += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"ROI credited for {credited} committees"
            )
        )
