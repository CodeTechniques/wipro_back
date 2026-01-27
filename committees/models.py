from django.db import models
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone


class Committee(models.Model):
    name = models.CharField(max_length=100)

    daily_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    monthly_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    yearly_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)


     # 👇 TEMPORARY (to stop Django guessing)
    annual_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15
    )

    duration_months = models.IntegerField(default=12)

    roi_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15
    )

    total_slots = models.IntegerField(default=0)

    filled_slots = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def slots_available(self):
        return self.total_slots - self.filled_slots

    def __str__(self):
        return self.name


class UserCommittee(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE)

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    total_invested = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    roi_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    roi_unlock_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.joined_at:
            self.joined_at = timezone.now()

        if not self.roi_unlock_date:
            self.roi_unlock_date = self.joined_at + timedelta(days=365)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.committee.name}"

        


class Investment(models.Model):
    user_committee = models.ForeignKey(
        UserCommittee,
        on_delete=models.CASCADE,
        related_name="investments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    investment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} on {self.investment_date}"


class Withdrawal(models.Model):
    user_committee = models.ForeignKey(
        UserCommittee,
        on_delete=models.CASCADE,
        related_name="withdrawals"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    is_roi = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)

    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} ({'ROI' if self.is_roi else 'Principal'})"




class PaymentPlan(models.Model):
    PLAN_TYPE_CHOICES = (
        ("daily", "Daily"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPE_CHOICES)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # interval in days (1 = daily, 30 = monthly, 365 = yearly)
    interval_days = models.PositiveIntegerField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ₹{self.amount}"





class CommitteePaymentPlan(models.Model):
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        related_name="payment_plans"
    )
    plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE)

    
    
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interval = models.PositiveIntegerField(help_text="Days", default=0)
    

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.committee.name} - {self.plan.name}"




from django.utils.timezone import now
from datetime import timedelta

class UserCommitteePlan(models.Model):
    user_committee = models.OneToOneField(
        UserCommittee,
        on_delete=models.CASCADE,
        related_name="active_plan"
    )

    plan = models.ForeignKey(PaymentPlan, on_delete=models.PROTECT)

    subscribed_at = models.DateTimeField(auto_now_add=True)
    next_due_at = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=True)

    next_payment_due = models.DateTimeField()
    last_payment_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.next_payment_due:
            self.next_payment_due = now() + timedelta(days=self.plan.interval_days)
        super().save(*args, **kwargs)
