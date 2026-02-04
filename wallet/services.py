from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    Wallet,
    WalletTransaction,
    PaymentRequest,
    PaymentTransaction,
    AdminWallet,
    AdminWalletEntry,
)

# =========================================================
# CORE WALLET OPERATIONS (SINGLE SOURCE OF TRUTH)
# =========================================================

@transaction.atomic
def credit_wallet(
    *,
    wallet: Wallet,
    amount: Decimal,
    tx_type: str,   # deposit | earned
    source: str,
    reference_id: str | None = None,
    note: str = "",
):
    """
    CREDIT wallet (Deposit / Earned)
    """
    if amount <= 0:
        raise ValueError("Credit amount must be positive")

    # 🔒 Idempotency
    if reference_id and WalletTransaction.objects.filter(
        wallet=wallet,
        tx_type=tx_type,
        reference_id=reference_id,
        status="success",
    ).exists():
        return None

    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        tx_type=tx_type,
        source=source,
        status="success",
        reference_id=reference_id,
        note=note,
    )

    # 💰 BALANCE UPDATE
    wallet.balance += amount

    # 📊 AGGREGATES
    if tx_type == "deposit":
        wallet.total_deposit += amount
    elif tx_type == "earned":
        wallet.total_earned += amount

    wallet.save()

    return tx


@transaction.atomic
def debit_wallet(
    *,
    wallet: Wallet,
    amount: Decimal,
    tx_type: str,   # withdraw | paid
    source: str,
    reference_id: str | None = None,
    note: str = "",
):
    """
    DEBIT wallet (Withdraw / Paid)
    """
    if amount <= 0:
        raise ValueError("Debit amount must be positive")

    if wallet.status != "active":
        raise ValueError("Wallet is frozen")

    if wallet.balance < amount:
        raise ValueError("Insufficient balance")

    # 🔒 Idempotency
    if reference_id and WalletTransaction.objects.filter(
        wallet=wallet,
        tx_type=tx_type,
        reference_id=reference_id,
        status="success",
    ).exists():
        return None

    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount=-amount,
        tx_type=tx_type,
        source=source,
        status="success",
        reference_id=reference_id,
        note=note,
    )

    # 💰 BALANCE UPDATE
    wallet.balance -= amount

    # 📊 AGGREGATES
    if tx_type == "withdraw":
        wallet.total_withdraw += amount
    elif tx_type == "paid":
        wallet.total_paid += amount

    wallet.save()

    return tx


# =========================================================
# PAYMENT REQUEST → WALLET (ADMIN APPROVAL)
# =========================================================

@receiver(post_save, sender=PaymentRequest)
def apply_payment_request_to_wallet(sender, instance, **kwargs):
    """
    Handles:
    - Deposit  → credit (deposit)
    - Withdraw → debit  (withdraw)
    """

    if instance.status != "approved":
        return

    # 🔒 Prevent double apply
    if instance.processed_at is not None:
        return

    wallet, _ = Wallet.objects.get_or_create(user=instance.user)

    try:
        if instance.request_type == "deposit":
            credit_wallet(
                wallet=wallet,
                amount=Decimal(instance.amount),
                tx_type="deposit",
                source="payment",
                reference_id=str(instance.id),  # ✅ STRING (FIXED)
                note="Admin approved deposit",
            )

            instance.earned = Decimal("0")
            instance.paid = Decimal("0")

        elif instance.request_type == "withdraw":
            debit_wallet(
                wallet=wallet,
                amount=Decimal(instance.amount),
                tx_type="withdraw",
                source="payment",
                reference_id=str(instance.id),  # ✅ STRING (FIXED)
                note="Admin approved withdrawal",
            )

            instance.paid = Decimal("0")
            instance.earned = Decimal("0")

        instance.processed_at = timezone.now()
        instance.save(update_fields=["earned", "paid", "processed_at"])

    except Exception as e:
        print("🔥 PAYMENT REQUEST SIGNAL ERROR:", e)
        raise


# =========================================================
# COMMITTEE / PROPERTY / SYSTEM PAYMENTS
# =========================================================

def apply_payment_transaction_to_wallet(payment_tx: PaymentTransaction):
    """
    Handles ALL PaymentTransaction → Wallet sync

    Supported flows:
    - Legacy platform payments        → paid (debit)
    - Committee investment (join/EMI) → committee_investment (debit)
    - Committee withdrawal            → withdraw (credit)
    """

    # ---------------------------
    # 🔒 SAFETY GUARDS
    # ---------------------------
    if payment_tx.status != "approved":
        return

    if payment_tx.wallet_synced:
        return

    if not payment_tx.amount or payment_tx.amount <= 0:
        return

    wallet = payment_tx.wallet or payment_tx.user.wallet

    try:
        with transaction.atomic():

            # ==================================================
            # 💸 COMMITTEE INVESTMENT (DEBIT)
            # ==================================================
            if (
                payment_tx.transaction_type == "investment"
                and payment_tx.user_committee
            ):
                debit_wallet(
                    wallet=wallet,
                    amount=Decimal(payment_tx.amount),
                    tx_type="committee_investment",
                    source="system",
                    reference_id=str(payment_tx.id),
                    note="Committee investment",
                )

                # Sync committee state
                payment_tx.user_committee.total_invested += payment_tx.amount
                payment_tx.user_committee.save(update_fields=["total_invested"])

            # ==================================================
            # 💰 COMMITTEE WITHDRAWAL (CREDIT)
            # ==================================================
            elif (
                payment_tx.transaction_type == "withdrawal"
                and payment_tx.user_committee
            ):
    # 💰 CREDIT WALLET (THIS IS THE WITHDRAW ENTRY)
                credit_wallet(
                    wallet=wallet,
                    amount=Decimal(payment_tx.amount),
                    tx_type="withdraw",          # 👈 THIS makes it a withdrawal in wallet
                    source="system",
                    reference_id=str(payment_tx.id),
                    note="Committee withdrawal approved",
                )

                # 🔻 Reduce committee investment
                payment_tx.user_committee.total_invested -= payment_tx.amount
                payment_tx.user_committee.save(update_fields=["total_invested"])

            # ==================================================
            # 🏷️ LEGACY / PLATFORM PAYMENTS (DEFAULT)
            # ==================================================
            else:
                debit_wallet(
                    wallet=wallet,
                    amount=Decimal(payment_tx.amount),
                    tx_type="paid",
                    source="system",
                    reference_id=str(payment_tx.id),
                    note="Platform usage payment",
                )

            # ==================================================
            # ✅ MARK AS SYNCED
            # ==================================================
            payment_tx.wallet_synced = True
            payment_tx.save(update_fields=["wallet_synced"])

    except Exception as e:
        print("🔥 PAYMENT TX WALLET ERROR:", e)
        raise


# =========================================================
# ADMIN WALLET (ACCOUNTING ONLY – NO USER BALANCE)
# =========================================================

def apply_payment_to_admin_wallet(payment_tx: PaymentTransaction):
    """
    Admin accounting wallet
    (Does NOT affect user wallet balance)
    """

    if payment_tx.amount is None:
        return

    admin_wallet, _ = AdminWallet.objects.get_or_create(
        user=payment_tx.user
    )

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

        admin_wallet.recalc_balance()
        admin_wallet.last_synced_payment = payment_tx
        admin_wallet.save(update_fields=["balance", "last_synced_payment"])
