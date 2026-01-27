from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from wallet.models import PaymentTransaction
from committees.models import UserCommitteePlan

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        plans = UserCommitteePlan.objects.filter(
            is_active=True,
            next_due_at__lte=now()
        )

        for up in plans:
            PaymentTransaction.objects.create(
                user=up.user_committee.user,
                user_committee=up.user_committee,
                transaction_type="investment",
                amount=up.plan.payment_amount,
                status="pending"
            )

            up.next_due_at = now() + timedelta(days=up.plan.interval)
            up.save()
