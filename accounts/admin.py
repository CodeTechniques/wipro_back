from django.contrib import admin
from .models import *
# Register your models here.
from django.contrib.auth.models import User
from django.contrib import admin

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_active")
    actions = ["block_users", "unblock_users"]

    def block_users(self, request, queryset):
        queryset.update(is_active=False)

    def unblock_users(self, request, queryset):
        queryset.update(is_active=True)





from django.contrib import admin
from .models import UserVerification


from django.contrib import admin
from django.utils.html import format_html
from .models import UserVerification


@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email",
        "phone_number",
        "aadhar_number",
        "pan_number",
        "passport_number",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")
    search_fields = (
        "user__username",
        "email",
        "phone_number",
        "aadhar_number",
        "pan_number",
        "passport_number",
        "international_id_number",
        "upi_id",
        "bank_account_number",
        "usdt_address",
    )

    readonly_fields = (
        "created_at",
        "updated_at",

        "aadhar_front_preview",
        "pan_card_preview",
        "passport_photo_preview",
        "international_id_photo_preview",
    )

    fieldsets = (
        ("User Info", {
            "fields": (
                "user",
                "email",
                "phone_number",
                "referred_by",
            )
        }),

        ("Indian KYC (Optional)", {
            "fields": (
                "aadhar_number",
                "aadhar_front_photo",
                "aadhar_front_preview",
                "pan_number",
                "pan_card_photo",
                "pan_card_preview",
            )
        }),

        ("Foreign KYC (Optional)", {
            "fields": (
                "passport_number",
                "passport_photo",
                "passport_photo_preview",
                "international_id_number",
                "international_id_photo",
                "international_id_photo_preview",
            )
        }),

        ("Withdrawal / Payment Details", {
            "fields": (
                "upi_id",
                "bank_name",
                "bank_account_number",
                "bank_ifsc_code",
                "usdt_address",
            )
        }),

        ("Verification Status", {
            "fields": ("status",)
        }),

        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    # =============================
    # 📷 IMAGE PREVIEWS (CLOUDINARY)
    # =============================

    def aadhar_front_preview(self, obj):
        if obj.aadhar_front_photo:
            return format_html(
                '<img src="{}" width="200" style="border-radius:6px;" />',
                obj.aadhar_front_photo.url
            )
        return "No Image"

    def pan_card_preview(self, obj):
        if obj.pan_card_photo:
            return format_html(
                '<img src="{}" width="200" style="border-radius:6px;" />',
                obj.pan_card_photo.url
            )
        return "No Image"

    def passport_photo_preview(self, obj):
        if obj.passport_photo:
            return format_html(
                '<img src="{}" width="200" style="border-radius:6px;" />',
                obj.passport_photo.url
            )
        return "No Image"

    def international_id_photo_preview(self, obj):
        if obj.international_id_photo:
            return format_html(
                '<img src="{}" width="200" style="border-radius:6px;" />',
                obj.international_id_photo.url
            )
        return "No Image"

    aadhar_front_preview.short_description = "Aadhaar Front Preview"
    pan_card_preview.short_description = "PAN Card Preview"
    passport_photo_preview.short_description = "Passport Preview"
    international_id_photo_preview.short_description = "International ID Preview"





@admin.register(ReferralLeaderboard)
class ReferralLeaderboardAdmin(admin.ModelAdmin):
    list_display = (
        "rank",
        "user",
        "period",
        "total_referrals",
        "total_earnings",
        "updated_at",
    )

    list_filter = ("period",)
    ordering = ("period", "rank")
    search_fields = ("user__username",)
