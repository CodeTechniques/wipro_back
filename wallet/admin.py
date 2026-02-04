from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.db import models

from .models import (
    Wallet,
    WalletTransaction,
    PaymentMethod,
    PaymentTransaction,
    PaymentRequest,
    WithdrawalRequest,
)

from .utils import get_referred_by_user
from wallet.services import apply_payment_to_admin_wallet

# =====================================================
# WALLET TRANSACTIONS (LEDGER – SAFE)
# =====================================================

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "wallet",
        "tx_type",
        "amount",
        "source",
        "status",
        "created_at",
    )
    list_filter = ("tx_type", "source", "status")
    search_fields = ("wallet__user__username",)
    readonly_fields = ("created_at",)


# =====================================================
# USER WALLET (DISPLAY ONLY – NO SIDE EFFECTS)
# =====================================================

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "referred_by",
        "balance",
        "bonus_balance",
        "status",
        "updated_at",
    )

    search_fields = ("user__username",)
    list_filter = ("status",)

    readonly_fields = (
        "referred_by",
        "balance",
        "updated_at",
    )

    fields = (
        "user",
        "referred_by",
        "balance",
        "bonus_balance",
        "status",
        "updated_at",
    )

    def referred_by(self, obj):
        ref = get_referred_by_user(obj.user)
        return ref.username if ref else "-"

    referred_by.short_description = "Referred By"


# =====================================================
# PAYMENT METHODS
# =====================================================

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "method_type",
        "for_investment",
        "for_withdrawal",
        "is_active",
    )
    list_filter = ("method_type", "for_investment", "for_withdrawal", "is_active")
    search_fields = ("name", "upi_id", "account_number")


# =====================================================
# PAYMENT TRANSACTIONS (ADMIN APPROVAL)
# =====================================================

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "user_committee",
        "transaction_type",
        "amount",
        "wallet_effect",
        "payment_method",
        "status",
        "created_at",
    )

    list_filter = ("transaction_type", "status", "payment_method")
    search_fields = ("user__username", "reference_id")

    readonly_fields = (
        "created_at",
        "processed_at",
        "payment_screenshot_preview",
    )

    fieldsets = (
        (None, {
            "fields": (
                "user",
                "user_committee",
                "transaction_type",
                "amount",
                "wallet_effect",
                "payment_method",
                "payment_screenshot_preview",
                "status",
                "admin_note",
            )
        }),
    )

    actions = ["approve_payment", "reject_payment"]

    def payment_screenshot_preview(self, obj):
        if not obj.payment_screenshot:
            return "No screenshot uploaded"
        return format_html(
            '<a href="{0}" target="_blank">'
            '<img src="{0}" style="max-height:300px;border-radius:8px;" />'
            '</a>',
            obj.payment_screenshot.url,
        )

    payment_screenshot_preview.short_description = "Payment Screenshot"

    def approve_payment(self, request, queryset):
        """
        IMPORTANT:
        - Admin wallet only
        - User wallet is handled by signals/services
        - No duplicate wallet logic here
        """
        for tx in queryset.filter(status="pending"):
            if not tx.wallet_effect:
                tx.wallet_effect = (
                    "credit"
                    if tx.transaction_type == "investment"
                    else "debit"
                )

            tx.status = "approved"
            tx.processed_at = timezone.now()
            tx.save(update_fields=["status", "processed_at", "wallet_effect"])

            # 🔥 ADMIN ACCOUNTING ONLY
            apply_payment_to_admin_wallet(tx)

        self.message_user(request, "Payments approved successfully")

    approve_payment.short_description = "Approve selected payments"

    def reject_payment(self, request, queryset):
        queryset.filter(status="pending").update(
            status="rejected",
            processed_at=timezone.now(),
        )
        self.message_user(request, "Payments rejected")

    reject_payment.short_description = "Reject selected payments"


# =====================================================
# PAYMENT REQUESTS (DEPOSIT / WITHDRAW)
# =====================================================

@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "request_type",
        "amount",
        "payment_method",
        "status",
        "created_at",
    )

    list_filter = ("request_type", "status")
    search_fields = ("user__username",)

    readonly_fields = (
        "created_at",
        "processed_at",
        "payment_screenshot_preview",
    )

    fieldsets = (
        (None, {
            "fields": (
                "user",
                "request_type",
                "amount",
                "payment_method",
                "payment_screenshot_preview",
                "user_payment_method_details",
                "status",
                "admin_message",
            )
        }),
    )

    actions = ["approve_payment", "reject_payment"]

    def payment_screenshot_preview(self, obj):
        if not obj.payment_screenshot:
            return "No screenshot uploaded"
        return format_html(
            '<a href="{0}" target="_blank">'
            '<img src="{0}" style="max-height:300px;border-radius:8px;" />'
            '</a>',
            obj.payment_screenshot.url,
        )

    payment_screenshot_preview.short_description = "Payment Screenshot"

    def approve_payment(self, request, queryset):
        queryset.filter(status="pending").update(
            status="approved",
            processed_at=timezone.now(),
        )
        self.message_user(request, "Payment requests approved")

    def reject_payment(self, request, queryset):
        queryset.filter(status="pending").update(
            status="rejected",
            processed_at=timezone.now(),
        )
        self.message_user(request, "Payment requests rejected")


# =====================================================
# WITHDRAWAL REQUESTS (PROXY MODEL)
# =====================================================

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "committee_name",
        "amount",
        "payment_method",
        "status",
        "created_at",
    )

    list_filter = ("status", "payment_method")
    search_fields = ("user__username", "user__email")

    readonly_fields = (
        "user",
        "user_committee",
        "amount",
        "payment_method",
        "created_at",
        "processed_at",
    )

    actions = ["approve_withdrawal", "reject_withdrawal"]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            transaction_type="withdrawal"
        )

    def committee_name(self, obj):
        if obj.user_committee and obj.user_committee.committee:
            return obj.user_committee.committee.name
        return "Wallet"

    committee_name.short_description = "Committee"

    def approve_withdrawal(self, request, queryset):
        queryset.filter(status="pending").update(
            status="approved",
            processed_at=timezone.now(),
            wallet_effect="debit",
        )
        self.message_user(request, "Withdrawal approved")

    def reject_withdrawal(self, request, queryset):
        queryset.filter(status="pending").update(
            status="rejected",
            processed_at=timezone.now(),
        )
        self.message_user(request, "Withdrawal rejected")
