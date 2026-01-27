from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .services import approve_loan

from django.contrib import admin
from decimal import Decimal
from django.utils.timezone import now
from datetime import timedelta

from .models import *



@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "committee",
        "committee_joined_at",
        "requested_amount",
        "requested_duration_months",
        "status",
        "created_at",
    )

    readonly_fields = (
        "user",
        "committee",
        "requested_amount",
        "requested_duration_months",
        "created_at",
    )

    def committee_joined_at(self, obj):
        return obj.committee.joined_at

    committee_joined_at.short_description = "Committee Joined At"



@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "principal_amount",
        "interest_percent",
        "emi_amount",
        "status",
    )

    readonly_fields = (
        "total_interest",
        "total_payable",
        "emi_amount",
        "approved_at",
    )

    fieldsets = (
        ("User Info", {
            "fields": ("user", "committee")
        }),
        ("Loan Inputs", {
            "fields": (
                "principal_amount",
                "interest_percent",
                "duration_months",
                "emi_interval_months",
            )
        }),
        ("Calculated Fields", {
            "fields": (
                "total_interest",
                "total_payable",
                "emi_amount",
            )
        }),
        ("Status", {
            "fields": ("status",)
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Auto-calculate loan + create EMI dues when admin saves loan
        """
        principal = Decimal(obj.principal_amount)
        interest_percent = Decimal(obj.interest_percent)
        duration = obj.duration_months
        emi_interval = obj.emi_interval_months

        # Calculate interest
        total_interest = (principal * interest_percent * duration) / Decimal(100)
        total_payable = principal + total_interest
        total_emis = duration // emi_interval
        emi_amount = total_payable / total_emis

        obj.total_interest = total_interest
        obj.total_payable = total_payable
        obj.emi_amount = emi_amount

        super().save_model(request, obj, form, change)

        # Create EMI dues ONLY when creating new loan
        if not change:
            due_date = now().date()

            for _ in range(total_emis):
                due_date += timedelta(days=30 * emi_interval)

                LoanDue.objects.create(
                    loan=obj,
                    due_amount=emi_amount,
                    due_date=due_date,
                    status="pending"
                )





@admin.register(LoanDue)
class LoanDueAdmin(admin.ModelAdmin):
    list_display = (
        "loan",
        "due_amount",
        "due_date",
        "status",
        "is_visible",   # ✅ MUST be here
    )

    list_filter = ("status", "is_visible", "due_date")

    list_editable = ("is_visible",)  # 🔥 toggle directly from list view


    search_fields = ("loan__user__username",)

    readonly_fields = ()

    fieldsets = (
        ("Loan EMI Info", {
            "fields": ("loan", "due_amount", "due_date")
        }),
        ("Visibility & Status", {
            "fields": ("status", "is_visible")
        }),
    )



@admin.register(UserLoan)
class UserLoanAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "loan_amount",
        "amount_paid",
        "emi_amount",
        "remaining_amount",
        "created_at",
    )

    readonly_fields = (
        "remaining_amount",
        "created_at",
    )
