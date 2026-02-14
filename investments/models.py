from django.db import models

# Create your models here.
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta


class Investment(models.Model):
    STATUS = [
        ("active", "Active"),
        ("withdrawn", "Withdrawn"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name="committee_investments"
)


    amount = models.DecimalField(max_digits=15, decimal_places=2)
    start_date = models.DateTimeField(default=now)
    interest_unlock_date = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS, default="active")
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.interest_unlock_date:
            self.interest_unlock_date = self.start_date + timedelta(days=365)
        super().save(*args, **kwargs)

    def is_interest_unlocked(self):
        return now() >= self.interest_unlock_date



from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

class GoldProduct(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    minimum_amount = models.DecimalField(max_digits=12, decimal_places=2)
    maximum_amount = models.DecimalField(max_digits=12, decimal_places=2)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GoldInvestment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    product = models.ForeignKey(
        GoldProduct,
        on_delete=models.PROTECT,
        related_name="investments"
    )

    grams = models.DecimalField(max_digits=10, decimal_places=10)
    buy_price_per_gram = models.DecimalField(max_digits=12, decimal_places=2)
    total_invested = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def current_value(self, current_price):
        return (self.grams * current_price).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    def profit_loss(self, current_price):
        return (
            self.grams * (current_price - self.buy_price_per_gram)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    def __str__(self):
        return f"{self.user.username} - {self.grams}g"


class GoldPrice(models.Model):
    price_per_gram = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.price_per_gram} {self.currency}"

class BondProduct(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    roi_percent = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months = models.IntegerField()

    minimum_amount = models.DecimalField(max_digits=12, decimal_places=2)
    maximum_amount = models.DecimalField(max_digits=12, decimal_places=2)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.roi_percent}% for {self.duration_months} months)"
    
class BondInvestment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bond_product = models.ForeignKey(
        BondProduct,
        on_delete=models.PROTECT,
        related_name="investments"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    start_date = models.DateTimeField(auto_now_add=True)
    maturity_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.maturity_date:
            self.maturity_date = timezone.now() + timezone.timedelta(
                days=self.bond_product.duration_months * 30
            )
        super().save(*args, **kwargs)

    def maturity_amount(self):
        return self.amount + (
            self.amount * self.bond_product.roi_percent / Decimal("100")
        )

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount}"
