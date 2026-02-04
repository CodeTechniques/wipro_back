from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Wallet
from wallet.models import PaymentTransaction
from wallet.services import apply_payment_transaction_to_wallet


@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)

@receiver(post_save, sender=PaymentTransaction)
def sync_payment_transaction(sender, instance, **kwargs):
    apply_payment_transaction_to_wallet(instance)
