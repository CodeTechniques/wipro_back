from decimal import Decimal
from django.db import transaction as db_tx, IntegrityError
from .models import Wallet, WalletTransaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from wallet.models import PaymentRequest

@db_tx.atomic
def credit_wallet(
    *,
    wallet: Wallet,
    amount: Decimal,
    tx_type: str,
    source: str,
    note: str = "",
    reference_id: str | None = None,
):
    """
    Credit wallet safely with idempotency.
    """
    # ✅ Idempotency check (code-level)
    if WalletTransaction.objects.filter(
        wallet=wallet,
        reference_id=reference_id,
        tx_type=tx_type,
        status="success",
    ).exists():
        return None  # already processed

    try:
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            tx_type=tx_type,
            source=source,
            status="success",
            note=note,
            reference_id=reference_id,
        )

        wallet.balance += amount
        wallet.save(update_fields=["balance"])

        return tx

    except IntegrityError:
        # ✅ DB-level idempotency fallback
        return None


@db_tx.atomic
def debit_wallet(
    *,
    wallet: Wallet,
    amount: Decimal,
    tx_type: str,
    source: str,
    note: str = "",
    reference_id: str | None = None,
):
    """
    Debit wallet safely with idempotency.
    """
    if wallet.status != "active":
        raise ValueError("Wallet is frozen")

    if wallet.balance < amount:
        raise ValueError("Insufficient balance")

    # ✅ Idempotency check
    if WalletTransaction.objects.filter(
        wallet=wallet,
        reference_id=reference_id,
        tx_type=tx_type,
        status="success",
    ).exists():
        return None  # already processed

    try:
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=-amount,
            tx_type=tx_type,
            source=source,
            status="success",
            note=note,
            reference_id=reference_id,
        )

        wallet.balance -= amount
        wallet.save(update_fields=["balance"])

        return tx

    except IntegrityError:
        return None


from .models import *


def approve_payment(self, request, queryset):
    for tx in queryset.filter(status="pending"):
        admin_wallet, _ = AdminWallet.objects.get_or_create(
            user=tx.user
        )

        if AdminWalletEntry.objects.filter(
            admin_wallet=admin_wallet,
            payment=tx
        ).exists():
            continue  # already applied

        if tx.transaction_type == "investment":
            AdminWalletEntry.objects.create(
                admin_wallet=admin_wallet,
                payment=tx,
                amount=tx.amount,
                entry_type="credit"
            )
            admin_wallet.total_credit += tx.amount

        elif tx.transaction_type == "withdrawal":
            AdminWalletEntry.objects.create(
                admin_wallet=admin_wallet,
                payment=tx,
                amount=tx.amount,
                entry_type="debit"
            )
            admin_wallet.total_debit += tx.amount

        admin_wallet.recalc_balance()

        tx.status = "approved"
        tx.save()




from django.db import transaction
from decimal import Decimal
from wallet.models import AdminWallet, AdminWalletEntry

def apply_payment_to_admin_wallet(payment_tx):
    if payment_tx.amount is None:
        return

    admin_wallet, _ = AdminWallet.objects.get_or_create(user=payment_tx.user)

    if AdminWalletEntry.objects.filter(
        admin_wallet=admin_wallet,
        payment=payment_tx
    ).exists():
        return

    with transaction.atomic():
        if payment_tx.transaction_type == "investment":
            admin_wallet.total_credit += payment_tx.amount
            entry_type = "credit"

        elif payment_tx.transaction_type == "withdrawal":
            admin_wallet.total_debit += payment_tx.amount
            entry_type = "debit"

        else:
            return

        AdminWalletEntry.objects.create(
            admin_wallet=admin_wallet,
            payment=payment_tx,
            amount=payment_tx.amount,
            entry_type=entry_type,
        )

        admin_wallet.balance = admin_wallet.total_credit - admin_wallet.total_debit
        admin_wallet.last_synced_payment = payment_tx
        admin_wallet.save()





from wallet.calculations import calculate_net_balance_for_user
from wallet.models import Wallet

def sync_wallet_for_user(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.balance = calculate_net_balance_for_user(user)
    wallet.save(update_fields=["balance"])


@receiver(post_save, sender=PaymentRequest)
def auto_apply_payment_request(sender, instance, created, **kwargs):
    """
    Automatically apply earned / paid when admin approves a payment request
    """

    # ✅ Only when approved
    if instance.status != "approved":
        return

    # ✅ Prevent double-application
    if instance.processed_at is None:
        instance.processed_at = timezone.now()

    # 🔒 Idempotency guard
    if instance.request_type == "deposit" and instance.earned:
        return

    if instance.request_type == "withdraw" and instance.paid:
        return

    # 🔥 APPLY LOGIC
    if instance.request_type == "deposit":
        instance.earned = Decimal(instance.amount)
        instance.paid = Decimal("0")

    elif instance.request_type == "withdraw":
        instance.paid = Decimal(instance.amount)
        instance.earned = Decimal("0")

    instance.save(update_fields=["earned", "paid", "processed_at"])


