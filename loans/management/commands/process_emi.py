from django.core.management.base import BaseCommand
from django.utils.timezone import now
from wallet.services import debit_wallet
from loans.models import Loan


class Command(BaseCommand):
    help = "Process EMI auto-debit"

    def handle(self, *args, **kwargs):
        loans = Loan.objects.filter(status="active")

        for loan in loans:
            emi_amount = loan.principal / loan.tenure_months

            try:
                debit_wallet(
                    wallet=loan.user.wallet,
                    amount=emi_amount,
                    tx_type="emi_debit",
                    source="system",
                    reference_id=loan.id,
                    note="Monthly EMI auto-debit"
                )
                self.stdout.write(f"EMI deducted for {loan.user.username}")

            except Exception:
                loan.status = "defaulted"
                loan.save(update_fields=["status"])

                # ❄️ Freeze wallet
                loan.user.wallet.status = "frozen"
                loan.user.wallet.save(update_fields=["status"])

                self.stdout.write(f"Loan defaulted: {loan.user.username}")
