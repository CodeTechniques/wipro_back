from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    TYPE = [
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("info", "Info"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name="system_notifications"
)


    title = models.CharField(max_length=120)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE, default="info")

    sender = models.CharField(max_length=50, default="Team WIPO")
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)




from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=100)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"



# notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from committees.models import Committee, PaymentPlan
from committees.models import UserCommittee

class DueNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, null=True, blank=True)
    plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE)

    user_committee = models.ForeignKey(
        UserCommittee,
        on_delete=models.CASCADE,
        null=True,          # 👈 TEMPORARY
        blank=True   
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    repeat_after_minutes = models.PositiveIntegerField(
        help_text="Notify user every X minutes if unpaid"
    )

    last_notified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Due ₹{self.amount} - {self.user}"




# notifications/models.py
from django.db import models
from django.contrib.auth.models import User

class DueResponse(models.Model):
    ACTION_CHOICES = (
        ("pay_now", "Pay Now"),
        ("pay_later", "Pay Later"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    due_notification = models.ForeignKey(
        "DueNotification",
        on_delete=models.CASCADE,
        related_name="responses"
    )

    committee = models.ForeignKey(
        "committees.Committee",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    plan = models.ForeignKey(
        "committees.PaymentPlan",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

     # ✅ FIX IS HERE
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "due_notification"],
                name="unique_user_due_response"
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.action}"







# notifications/models.py

class CommitteePaymentDue(models.Model):
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE)
    plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    repeat_after_minutes = models.PositiveIntegerField(default=60)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.committee.name} - {self.plan.name} - ₹{self.amount}"




# notifications/models.py

from django.db import models
from django.contrib.auth.models import User

class UniversalDue(models.Model):
    CONTEXT_CHOICES = (
        ("loan", "Loan"),
        ("committee", "Committee"),
        ("wallet", "Wallet"),
        ("custom", "Custom"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="universal_dues"
    )

    # 🔹 WHERE this due belongs
    context = models.CharField(
        max_length=20,
        choices=CONTEXT_CHOICES
    )

    reference_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="loan_id / loan_due_id / committee_id / etc"
    )

    # 🔹 WHAT admin writes
    heading = models.CharField(
        max_length=120,
        help_text="Short title e.g. EMI Due, Payment Reminder"
    )

    description = models.TextField(
        help_text="Detailed message shown to user"
    )

    # 🔹 MONEY
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    # 🔹 REMINDER SETTINGS
    repeat_after_minutes = models.PositiveIntegerField(default=60)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    # 🔹 STATUS
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} | {self.context} | ₹{self.amount}"




class UniversalDueResponse(models.Model):
    ACTION_CHOICES = (
        ("pay_now", "Pay Now"),
        ("pay_later", "Pay Later"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    due = models.ForeignKey(
        UniversalDue,
        on_delete=models.CASCADE,
        related_name="responses"
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "due"],
                name="unique_universal_due_response"
            )
        ]
