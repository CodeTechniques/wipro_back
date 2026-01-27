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
