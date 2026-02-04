

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import uuid



class Wallet(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("frozen", "Frozen"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    total_deposit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_withdraw = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet({self.user.username})"


class WalletTransaction(models.Model):
    TX_TYPE = [
        ("deposit", "Deposit"),
        ("withdraw", "Withdraw"),
         ("earned", "Earned"),
         ("paid", "Paid"),
        ("committee_investment", "Committee Investment"),
        ("property_payment", "Property Payment"),
        ("interest", "Interest"),
        ("admin_adjustment", "Admin Adjustment"),
        ("loan_credit", "Loan Credit"),
        ("emi_debit", "EMI Debit"),
    ]

    SOURCE = [
        ("system", "System"),
        ("admin", "Admin"),
        ("payment", "Payment"),
    ]

    STATUS = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")

    # 🔥 IMPORTANT: signed amount
    # +1000 = credit
    # -1000 = debit
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    tx_type = models.CharField(max_length=30, choices=TX_TYPE)
    source = models.CharField(max_length=20, choices=SOURCE)
    status = models.CharField(max_length=20, choices=STATUS, default="success")

    reference_id = models.CharField(max_length=100, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tx_type} | {self.amount}"



from django.db import models
from django.contrib.auth.models import User
from committees.models import UserCommittee


class PaymentMethod(models.Model):
    METHOD_TYPE_CHOICES = (
        ("upi", "UPI"),
        ("bank", "Bank Transfer"),
        ("usdt", "USDT / Crypto"),
    )

    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE_CHOICES)

    # Admin provided details
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_holder = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    usdt_address = models.CharField(max_length=255, blank=True, null=True)

    # Usage flags
    for_investment = models.BooleanField(default=True)
    for_withdrawal = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.method_type.upper()})"



class PaymentTransaction(models.Model):
    TRANSACTION_TYPE = (
        ("investment", "Investment"),
        ("withdrawal", "Withdrawal"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("overdue", "Overdue"),
        ],
        default="pending"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_committee = models.ForeignKey(
    UserCommittee,
    on_delete=models.CASCADE,
    related_name="payments",
    null=True,
    blank=True
)
    
    admin_message = models.TextField(
        blank=True,
        help_text="Message shown to user after approval/rejection"
    )

    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, null=True, blank=True)

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Set by admin on approval"
    )

    withdrawal_details = models.TextField(
        blank=True,
        null=True,
        help_text="Bank / UPI / USDT details for withdrawal"
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="UPI ref / bank txn id / hash"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    admin_note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    is_recurring = models.BooleanField(default=False)

    wallet = models.ForeignKey(
        "Wallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions"
    )

    wallet_effect = models.CharField(
        max_length=10,
        choices=[("credit", "Credit"), ("debit", "Debit")],
        null=True,
        blank=True
    )

    wallet_synced = models.BooleanField(default=False)

    payment_screenshot = models.ImageField(
        "payment_screenshot",
        null=True,
        blank=True,
        help_text="User uploaded payment proof"
    )


    def __str__(self):
     committee_name = (
        self.user_committee.committee.name
        if self.user_committee and self.user_committee.committee
        else "Wallet"
    )

     return (
        f"{self.user.username} | "
        f"{self.transaction_type} | "
        f"₹{self.amount} | "
        f"{committee_name} | "
        f"{self.status}"
    )


class WithdrawalRequest(PaymentTransaction):
    class Meta:
        proxy = True
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"

    def __str__(self):
        committee_name = (
            self.user_committee.committee.name
            if self.user_committee and self.user_committee.committee
            else "Wallet"
        )

        return (
            f"{self.user.username} | "
            f"Withdrawal | "
            f"₹{self.amount} | "
            f"{committee_name} | "
            f"{self.status}"
        )

from django.db import models
from django.contrib.auth.models import User

class PaymentRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    TYPE_CHOICES = (
        ("deposit", "Deposit"),
        ("withdraw", "Withdraw"),
    )

    # ✅ NEW FIELD
    request_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        help_text="Deposit or Withdraw",
        null=True,
        blank=True,
    )

    # ✅ SCREENSHOT (same as PaymentTransaction)
    payment_screenshot = models.ImageField(
        "payment_screenshot",
        null=True,
        blank=True,
        help_text="User uploaded payment proof"
    )

     # ✅ THIS IS THE FIELD YOU WANT
    user_payment_method_details = models.TextField(
        null=True,
        blank=True,
        help_text="User provided UPI / Bank / USDT details for withdrawal"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # purpose = models.CharField(
    #     max_length=50,
    #     help_text="loan emi / wallet topup / investment"
    # )

    payment_method = models.ForeignKey(
        "PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

     # 🔥 NEW FIELDS (CORE)
    earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount added to user's wallet"
    )

    paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount deducted from user's wallet"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    admin_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} | {self.amount} | {self.status}"





class AdminWallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_wallet"
    )

    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    last_synced_payment = models.ForeignKey(
        "PaymentTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    updated_at = models.DateTimeField(auto_now=True)

    def recalc_balance(self):
        self.balance = self.total_credit - self.total_debit
        self.save(update_fields=["balance"])

    def __str__(self):
        return f"AdminWallet({self.user.username})"



class AdminWalletEntry(models.Model):
    admin_wallet = models.ForeignKey(
        AdminWallet,
        on_delete=models.CASCADE,
        related_name="entries"
    )

    payment = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.PROTECT
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    entry_type = models.CharField(
        max_length=10,
        choices=[("credit", "Credit"), ("debit", "Debit")]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("admin_wallet", "payment")
