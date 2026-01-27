from django.db import models

# Create your models here.
from django.conf import settings

User = settings.AUTH_USER_MODEL


class UserVerification(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="verification"
    )

    email = models.EmailField(blank=True, null=True)


    phone_number = models.CharField(max_length=15)
    aadhar_number = models.CharField(max_length=12)
    pan_number = models.CharField(max_length=10)

    # 📷 Photo fields
    aadhar_front_photo = models.ImageField(
        upload_to="verification/aadhar_front/",
        blank=True,
        null=True
    )
    pan_card_photo = models.ImageField(
        upload_to="verification/pan_card/",
        blank=True,
        null=True
    )

    # 🔗 Referral (keep blank for now)
    referred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_users"
    )

    # 🌍 FOREIGN CLIENT DOCUMENTS (OPTIONAL)
    passport_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    passport_photo = models.ImageField(
        upload_to="verification/passport/",
        blank=True,
        null=True
    )

    international_id_number = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )
    international_id_photo = models.ImageField(
        upload_to="verification/international_id/",
        blank=True,
        null=True
    )

     # 💳 USER WITHDRAWAL PAYMENT DETAILS (OPTIONAL)
    upi_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    bank_ifsc_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    usdt_address = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    # ✅ Status dropdown
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.status}"





# accounts/models.py (or users/models.py)

from django.contrib.auth.models import User
from django.db import models
import uuid

class UserReferral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    referral_code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals"
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = f"WIP{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.referral_code}"





class ReferralEarning(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    referred_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="earned_from"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} earned ₹{self.amount}"




class ReferralLeaderboard(models.Model):
    PERIOD_CHOICES = (
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)

    total_referrals = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2)

    rank = models.PositiveIntegerField()

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "period")
        ordering = ["rank"]

    def __str__(self):
        return f"{self.user} ({self.period}) Rank {self.rank}"





from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    profile_pic = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    location = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username