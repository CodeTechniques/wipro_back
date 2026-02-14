# Register your models here.
from django.contrib import admin
from .models import Committee


from committees.services.roi_service import calculate_total_return
from .models import *

@admin.register(UserCommittee)
class UserCommitteeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "committee",
        "subscribed_plan",
        "payment_frequency",
        "roi_info",
        "joined_at",
        "is_active",
    )

    list_filter = (
        "committee",
        "is_active",
    )

    search_fields = (
        "user__username",
        "committee__name",
    )

    def subscribed_plan(self, obj):
        if hasattr(obj, "active_plan") and obj.active_plan:
            return obj.active_plan.plan.name
        return "—"
    subscribed_plan.short_description = "Subscribed Plan"

    def payment_frequency(self, obj):
        if hasattr(obj, "active_plan") and obj.active_plan:
            return obj.active_plan.plan.plan_type.upper()
        return "—"
    payment_frequency.short_description = "Frequency"

    def roi_info(self, obj):
        data = calculate_total_return(obj)
        return f"₹{data['roi']} (Total: ₹{data['total_return']})"

    list_display = ("user", "committee", "roi_info")

    def roi_info(self, obj):
        data = calculate_total_return(obj)
        return f"₹{data['roi']} (Total: ₹{data['total_return']})"



from django.contrib import admin
from .models import Committee
from decimal import Decimal


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):

   
   
    readonly_fields = (
        "yearly_total_invested",
        "yearly_roi_amount",
        "yearly_total_return",
        
    )

    fieldsets = (
        ("Committee Info", {
            "fields": (
                "name",
                "is_active",
            )
        }),

        ("Slots Configuration", {
            "fields": (
                "total_slots",
                "filled_slots",
            )
        }),

        ("💰 Daily Plan", {
            "fields": (
                "daily_amount",
            )
        }),

        ("💰 Monthly Plan", {
            "fields": (
                "monthly_amount",
            )
        }),

        

        ("Yearly Investment", {
            "fields": (
                "yearly_amount",
                "duration_months",
                "roi_percent",
            )
        }),
        ("📊 Yearly ROI Calculator", {
            "fields": (
                "yearly_total_invested",
                "yearly_roi_amount",
                "yearly_total_return",
            )
        }),
    )

    # 🔹 Total Invested
    def yearly_total_invested(self, obj):
        if not obj.pk or not obj.yearly_amount:
            return "—"
        years = Decimal(obj.duration_months) / Decimal(12)
        return f"₹ {obj.yearly_amount * years}"

    yearly_total_invested.short_description = "Total Invested (Yearly)"

    # 🔹 ROI Amount
    def yearly_roi_amount(self, obj):
        if not obj.pk or not obj.yearly_amount:
            return "—"
        years = Decimal(obj.duration_months) / Decimal(12)
        roi = (obj.yearly_amount * years) * (obj.roi_percent / Decimal(100))
        return f"₹ {roi}"

    yearly_roi_amount.short_description = "ROI Amount (Annual)"

    # 🔹 Total Return
    def yearly_total_return(self, obj):
        if not obj.pk or not obj.yearly_amount:
            return "—"
        years = Decimal(obj.duration_months) / Decimal(12)
        total = obj.yearly_amount * years
        roi = total * (obj.roi_percent / Decimal(100))
        return f"₹ {total + roi}"

    yearly_total_return.short_description = "Total Return After Duration"





@admin.register(UserCommitteePlan)
class UserCommitteePlanAdmin(admin.ModelAdmin):
    list_display = (
        "user_committee",
        "plan",
        "next_payment_due",
        "last_payment_at",
        "is_active",
    )

    list_filter = (
        "plan__plan_type",
        "is_active",
    )





from .models import CommitteePaymentPlan

@admin.register(CommitteePaymentPlan)
class CommitteePaymentPlanAdmin(admin.ModelAdmin):
    list_display = (
        "committee",
        "plan_name",
        "plan_type",
        "payment_amount",
        "interval_display",
        "is_active",
    )

    list_filter = (
        "committee",
        "plan__plan_type",
        "is_active",
    )

    search_fields = (
        "committee__name",
        "plan__name",
    )

    fieldsets = (
        ("Committee", {
            "fields": ("committee",),
        }),
        ("Payment Plan Configuration", {
            "fields": (
                "plan",
                "payment_amount",
                "interval",
                "is_active",
            ),
            "description": (
                "Define how much the user pays and how often "
                "for this committee."
            ),
        }),
    )

    def plan_name(self, obj):
        return obj.plan.name
    plan_name.short_description = "Plan Name"

    def plan_type(self, obj):
        return obj.plan.plan_type.upper()
    plan_type.short_description = "Type"

    def interval_display(self, obj):
        return f"Every {obj.interval} days"
    interval_display.short_description = "Payment Interval"

    list_display = (
        "committee",
        "plan_type_display",
        "amount_display",
        "interval_display",
        "is_active",
    )

    list_filter = (
        "plan",
        "is_active",
    )

    search_fields = (
        "committee__name",
    )

    def plan_type_display(self, obj):
        return obj.plan
    plan_type_display.short_description = "Plan Type"

    def amount_display(self, obj):
        return f"₹{obj.payment_amount}"
    amount_display.short_description = "Amount"

    def interval_display(self, obj):
        return f"{obj.interval} days"
    interval_display.short_description = "Interval"


from .models import PaymentPlan

@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "plan_type",
        "amount",
        "interval_days",
        "is_active",
    )

    list_filter = ("plan_type", "is_active")

    search_fields = ("name",)

    fieldsets = (
        ("Plan Info", {
            "fields": (
                "name",
                "plan_type",
                "amount",
                "interval_days",
                "is_active",
            )
        }),
    )
