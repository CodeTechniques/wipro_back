from django.contrib import admin

# Register your models here.
# properties/admin.py

from django.contrib import admin
from django.db.models import Count
from .models import Property, PropertyImage



# @admin.register(Property)
# class PropertyAdmin(admin.ModelAdmin):
#     list_display = (
#         "title",
#         "owner",
#         "property_type",
#         "listing_type",
#         "status",
#         "price",
#         "city",
#         "is_verified",
#         "created_at",
#     )

#     list_filter = (
#         "status",
#         "property_type",
#         "listing_type",
#         "city",
#     )

#     search_fields = (
#         "title",
#         "owner__username",
#         "owner__email",
#         "city",
#         "location",
#     )

#     ordering = ("-created_at", "is_verified")

#     list_filter = ("status", "is_verified")

#     actions = ["mark_available"]

#     readonly_fields = ("views_count", "created_at", "updated_at")

#     fieldsets = (
#         ("Basic Info", {
#             "fields": ("title", "description", "owner")
#         }),
#         ("Property Details", {
#             "fields": (
#                 "property_type",
#                 "listing_type",
#                 "status",
#                 "price",
#                 "rent_price",
#                 "area_sqft",
#                 "bedrooms",
#                 "bathrooms",
#             )
#         }),
#         ("Location", {
#             "fields": ("location", "address", "city", "state", "pincode")
#         }),
#         ("Stats", {
#             "fields": ("views_count", "created_at", "updated_at")
#         }),

#     @admin.action(description="Mark selected properties as AVAILABLE")
#         def mark_available(self, request, queryset):
#         queryset.filter(
#             status="draft",
#             is_verified=True
#         ).update(status="available")
#     )


from django.contrib import admin
from .models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "property_type",
        "listing_type",
        "status",
        "price",
        "city",
        "is_verified",
        "created_at",
    )

    list_filter = (
        "status",
        "is_verified",
        "property_type",
        "listing_type",
        "city",
    )

    search_fields = (
        "title",
        "owner__username",
        "owner__email",
        "city",
        "location",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "views_count",
        "created_at",
        "updated_at",
    )

    actions = ["mark_available"]

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "title",
                "description",
                "owner",
            )
        }),
        ("Property Details", {
            "fields": (
                "property_type",
                "listing_type",
                "status",
                "price",
                "rent_price",
                "area_sqft",
                "bedrooms",
                "bathrooms",
            )
        }),
        ("Location", {
            "fields": (
                "location",
                "address",
                "city",
                "state",
                "pincode",
            )
        }),
        ("Verification & Stats", {
            "fields": (
                "is_verified",
                "views_count",
                "created_at",
                "updated_at",
            )
        }),
    )

    # 🔥 ADMIN ACTION
    @admin.action(description="Mark selected properties as AVAILABLE")
    def mark_available(self, request, queryset):
        queryset.filter(
            status="draft",
            is_verified=True
        ).update(status="available")



from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "property_count",
        "is_staff",
        "is_active",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(property_count=Count("property"))

    def property_count(self, obj):
        return obj.property_count

    property_count.admin_order_field = "property_count"
    property_count.short_description = "Properties Created"





@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "is_primary", "created_at")
    list_filter = ("is_primary",)



from django.contrib import admin
from .models import PropertyInterest, PurchasePlan



from django.contrib import admin
from .models import PropertyInterest, PurchasePlan


@admin.register(PropertyInterest)
class PropertyInterestAdmin(admin.ModelAdmin):
    list_display = (
        "property_title",
        "property_owner",
        "requested_by",
        "payment_mode",
        "group_size",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "plan__mode",
        "property__city",
    )

    search_fields = (
        "property__title",
        "requester__username",
        "property__owner__username",
    )

    readonly_fields = (
        "property",
        "requester",
        "plan",
        "message",
        "created_at",
    )

    fieldsets = (
        ("Property Info", {
            "fields": (
                "property",
                "property_owner_display",
            )
        }),
        ("Requester Info", {
            "fields": (
                "requester",
                "message",
            )
        }),
        ("Payment Plan", {
            "fields": (
                "payment_mode_display",
                "group_size_display",
            )
        }),
        ("Status", {
            "fields": (
                "status",
                "created_at",
            )
        }),
    )

    # ---------- DISPLAY HELPERS ----------

    def property_title(self, obj):
        return obj.property.title

    def property_owner(self, obj):
        return obj.property.owner.username

    def requested_by(self, obj):
        return obj.requester.username

    def payment_mode(self, obj):
        return obj.plan.mode if obj.plan else "-"

    def group_size(self, obj):
        if obj.plan and obj.plan.mode == "group":
            return obj.plan.group_size
        return "-"

    # ---------- FORM DISPLAY (READABLE LABELS) ----------

    def property_owner_display(self, obj):
        return obj.property.owner.username

    def payment_mode_display(self, obj):
        return obj.plan.get_mode_display()

    def group_size_display(self, obj):
        if obj.plan.mode == "group":
            return obj.plan.group_size
        return "Single Payment"

    property_title.short_description = "Property"
    property_owner.short_description = "Owner"
    requested_by.short_description = "Requested By"
    payment_mode.short_description = "Payment Mode"
    group_size.short_description = "Group Size"

    property_owner_display.short_description = "Property Owner"
    payment_mode_display.short_description = "Payment Mode"
    group_size_display.short_description = "Group Size"


@admin.register(PurchasePlan)
class PurchasePlanAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "created_by",
        "mode",
        "group_size",
        "base_price",
        "total_payable",
        "status",
        "created_at",
    )

    list_filter = ("mode", "status")

    readonly_fields = (
        "property",
        "created_by",
        "mode",
        "group_size",
        "base_price",
        "gst_percent",
        "platform_percent",
        "total_payable",
        "created_at",
    )

    fieldsets = (
        ("Property", {
            "fields": ("property",)
        }),
        ("Created By", {
            "fields": ("created_by",)
        }),
        ("Payment Mode", {
            "fields": ("mode", "group_size")
        }),
        ("Pricing", {
            "fields": (
                "base_price",
                "gst_percent",
                "platform_percent",
                "total_payable",
            )
        }),
        ("Status", {
            "fields": ("status", "created_at")
        }),
    )




from django.contrib import admin
from .models import PropertyRequest


@admin.register(PropertyRequest)
class PropertyRequestAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "property",
        "property_owner",
        "payment_mode",
        "group_size_display",
        "status",
        "created_at",
    )

    list_filter = ("status", "payment_mode", "property__city")
    search_fields = ("full_name", "property__title", "property__owner__username")

    readonly_fields = (
        "user",
        "property",
        "property_owner_display",
        "created_at",
    )

    fieldsets = (
        ("Property Info", {
            "fields": ("property", "property_owner_display")
        }),
        ("User Form Data", {
            "fields": ("full_name", "age", "occupation")
        }),
        ("Payment", {
            "fields": ("payment_mode", "group_size")
        }),
        ("Admin Decision", {
            "fields": ("status",)
        }),
        ("System", {
            "fields": ("user", "created_at")
        }),
    )

    def property_owner(self, obj):
        return obj.property.owner.username

    def property_owner_display(self, obj):
        return obj.property.owner.username

    def group_size_display(self, obj):
        return obj.group_size if obj.payment_mode == "group" else "Single"

    property_owner.short_description = "Owner"
    property_owner_display.short_description = "Property Owner"
    group_size_display.short_description = "Group Size"







from django.contrib import admin
from django.utils.html import format_html
from .models import PropertyListingRequest


@admin.register(PropertyListingRequest)
class PropertyListingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "property_title",
        "property_owner",
        "listing_fee",
        "payment_status",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "is_paid",
        "created_at",
    )

    search_fields = (
        "property__title",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "property",
        "user",
        "listing_fee",
        "created_at",
        "paid_at",
    )

    fieldsets = (
        ("Property Info", {
            "fields": (
                "property",
                "user",
            )
        }),
        ("Payment Info", {
            "fields": (
                "listing_fee",
                "is_paid",
                "paid_at",
            )
        }),
        ("Admin Decision", {
            "fields": (
                "status",
            )
        }),
        ("System", {
            "fields": (
                "created_at",
            )
        }),
    )

    actions = ["approve_listing", "reject_listing"]

    # 🔹 DISPLAY HELPERS

    def property_title(self, obj):
        return obj.property.title

    def property_owner(self, obj):
        return obj.user.username

    def payment_status(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">PAID</span>')
        return format_html('<span style="color: red;">UNPAID</span>')

    property_title.short_description = "Property"
    property_owner.short_description = "Owner"
    payment_status.short_description = "Payment"

    # 🔹 ADMIN ACTIONS

    @admin.action(description="Approve selected listings")
    def approve_listing(self, request, queryset):
        for req in queryset:
            if not req.is_paid:
                continue  # ❌ cannot approve unpaid

            req.status = "approved"
            req.save(update_fields=["status"])

            # 🔥 ensure property is verified
            prop = req.property
            prop.is_verified = True
            prop.save(update_fields=["is_verified"])

    @admin.action(description="Reject selected listings")
    def reject_listing(self, request, queryset):
        queryset.update(status="rejected")
