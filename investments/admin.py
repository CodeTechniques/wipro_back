from django.contrib import admin
from .models import BondProduct

@admin.register(BondProduct)
class BondProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "roi_percent",
        "duration_months",
        "minimum_amount",
        "maximum_amount",
        "is_active",
    )

from .models import GoldProduct

@admin.register(GoldProduct)
class GoldProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "minimum_amount",
        "maximum_amount",
        "is_active",
    )



from .models import BondInvestment


@admin.register(BondInvestment)
class BondInvestmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "bond_product",
        "amount",
        "roi_percent_display",
        "start_date",
        "maturity_date",
        "is_active",
    )

    list_filter = (
        "bond_product",
        "is_active",
        "start_date",
    )

    search_fields = (
        "user__username",
        "user__email",
        "bond_product__name",
    )

    readonly_fields = (
        "user",
        "bond_product",
        "amount",
        "start_date",
        "maturity_date",
    )

    def roi_percent_display(self, obj):
        return obj.bond_product.roi_percent
    roi_percent_display.short_description = "ROI %"

from .models import GoldInvestment


@admin.register(GoldInvestment)
class GoldInvestmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "product",
        "grams",
        "buy_price_per_gram",
        "total_invested",
        "created_at",
        "is_active",
    )

    list_filter = (
        "product",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "product__name",
    )

    readonly_fields = (
        "user",
        "product",
        "grams",
        "buy_price_per_gram",
        "total_invested",
        "created_at",
    )
