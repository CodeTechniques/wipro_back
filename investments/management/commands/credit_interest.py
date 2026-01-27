from django.core.management.base import BaseCommand
from django.utils.timezone import now
from decimal import Decimal
from investments.models import Investment
from wallet.services import credit_wallet


class Command(BaseCommand):
    help = "Credit 15% interest for eligible investments"

    def handle(self, *args, **kwargs):
        investments = Investment.objects.filter(
            status="active",
            interest_unlock_date__lte=now()
        )

        for inv in investments:
            interest_amount = inv.amount * Decimal("0.15")

            credit_wallet(
                wallet=inv.user.wallet,
                amount=interest_amount,
                tx_type="interest",
                source="system",
                reference_id=inv.id,
                note="15% annual investment interest credited"
            )

            self.stdout.write(
                f"Interest credited for {inv.user.username}: {interest_amount}"
            )
