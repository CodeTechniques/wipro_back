from django.db import models

# Create your models here.
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from committees.models import *  # Import UserCommittee or adjust the import path based on where it's defined


class LoanApplication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    committee = models.ForeignKey(UserCommittee, on_delete=models.CASCADE)

    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    requested_duration_months = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending"
    )

    admin_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)




class Loan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    committee = models.ForeignKey(UserCommittee, on_delete=models.CASCADE, blank=True, null=True)

    principal_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    interest_percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    duration_months = models.PositiveIntegerField(blank=True, null=True)
    emi_interval_months = models.PositiveIntegerField(blank=True, null=True)

    total_interest = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("completed", "Completed")],
        default="active"
    )

    approved_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)





class LoanDue(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)

    due_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("overdue", "Overdue"),
        ],
        default="pending"
    )

    # 🔹 NEW FIELD
    is_visible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.loan} - {self.due_amount} - {self.due_date}"




class UserLoan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)

    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def remaining_amount(self):
     if self.loan_amount is None:
            return 0
     if self.amount_paid is None:
            return self.loan_amount
     return self.loan_amount - self.amount_paid

    def __str__(self):
        return f"{self.user.username} - Loan Wallet"




