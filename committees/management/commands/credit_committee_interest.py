from django.core.management.base import BaseCommand
from committees.models import CommitteeMembership
from committees.services import credit_daily_interest


class Command(BaseCommand):
    help = "Credit daily interest for all active committee memberships"

    def handle(self, *args, **options):
        qs = CommitteeMembership.objects.select_related(
            "committee", "user", "user__wallet"
        ).filter(status="active")

        credited = 0

        for membership in qs:
            result = credit_daily_interest(membership)
            if result:
                credited += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Daily interest credited for {credited} memberships"
            )
        )
