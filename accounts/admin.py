from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import UserVerification, ReferralLeaderboard


# ================================
# 🔹 INLINE VERIFICATION IN USER
# ================================
class UserVerificationInline(admin.StackedInline):
    model = UserVerification
    fk_name = "user"   # 🔥 IMPORTANT FIX
    can_delete = False
    extra = 0


# ================================
# 🔹 USER ADMIN
# ================================
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active")

    # show verification inside user page
    inlines = [UserVerificationInline]

    # ❌ remove permission UI
    filter_horizontal = ()
    fieldsets = (
        ("Basic Info", {
            "fields": ("username", "email", "password")
        }),
        ("Personal Info", {
            "fields": ("first_name", "last_name")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Dates", {
            "fields": ("last_login", "date_joined"),
        }),
    )

    actions = ["block_users", "unblock_users"]

    def block_users(self, request, queryset):
        queryset.update(is_active=False)

    def unblock_users(self, request, queryset):
        queryset.update(is_active=True)


# ================================
# 🔹 USER VERIFICATION ADMIN PAGE
# ================================
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
    search_fields = ("user__username", "email", "phone_number")

    readonly_fields = (
        "created_at",
        "updated_at",
        "aadhar_front_preview",
        "aadhar_back_preview",
        "pan_card_preview",
        "passport_photo_preview",
        "international_id_photo_preview",
    )

    # IMAGE PREVIEWS
    def aadhar_front_preview(self, obj):
        if obj.aadhar_front_photo:
            return format_html('<img src="{}" width="200"/>', obj.aadhar_front_photo.url)
        return "No Image"

    def aadhar_back_preview(self, obj):
        if obj.aadhar_back_photo:
            return format_html('<img src="{}" width="200"/>', obj.aadhar_back_photo.url)
        return "No Image"

    def pan_card_preview(self, obj):
        if obj.pan_card_photo:
            return format_html('<img src="{}" width="200"/>', obj.pan_card_photo.url)
        return "No Image"

    def passport_photo_preview(self, obj):
        if obj.passport_photo:
            return format_html('<img src="{}" width="200"/>', obj.passport_photo.url)
        return "No Image"

    def international_id_photo_preview(self, obj):
        if obj.international_id_photo:
            return format_html('<img src="{}" width="200"/>', obj.international_id_photo.url)
        return "No Image"


# ================================
# 🔹 REFERRAL LEADERBOARD
# ================================
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
    search_fields = ("user__username",)
