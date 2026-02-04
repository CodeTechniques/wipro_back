from django.db.models.signals import post_save
from django.dispatch import receiver
from wallet.services import debit_wallet
from wallet.models import PaymentTransaction

@receiver(post_save, sender=PaymentTransaction)
def apply_committee_payment(sender, instance, **kwargs):
    if instance.status != "approved":
        return

    if instance.wallet_synced:
        return

    if instance.transaction_type != "investment":
        return

    wallet = instance.user.wallet

    debit_wallet(
        wallet=wallet,
        amount=instance.amount,
        tx_type="committee_investment",
        source="system",
        reference_id=str(instance.id),
        note="Committee recurring investment",
    )

    # 🔁 Sync business model
    if instance.user_committee:
        instance.user_committee.total_invested += instance.amount
        instance.user_committee.save(update_fields=["total_invested"])

    instance.wallet_synced = True
    instance.save(update_fields=["wallet_synced"])
