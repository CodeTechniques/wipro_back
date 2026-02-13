from decimal import Decimal
from django.utils.timezone import now
from wallet.services import credit_wallet, debit_wallet
from .models import Investment


def create_investment(*, user, amount):
    investment = Investment.objects.create(
        user=user,
        amount=amount,
    )

    credit_wallet(
        wallet=user.wallet,
        amount=amount,
        tx_type="investment",
        source="system",
        reference_id=investment.id,
        note="Investment created",
    )

    return investment


from decimal import Decimal
from django.utils.timezone import now

ANNUAL_RATE = Decimal("0.15")
DAYS_IN_YEAR = Decimal("365")


def calculate_accrued_interest(principal: Decimal, start_date):
    """
    Interest accrues from DAY 1.
    Paid only if >= 365 days completed.
    """
    days_invested = Decimal((now() - start_date).days)

    if days_invested < DAYS_IN_YEAR:
        return Decimal("0.00")  # locked interest

    interest = principal * ANNUAL_RATE * (days_invested / DAYS_IN_YEAR)
    return interest.quantize(Decimal("0.01"))



def withdraw_investment(*, investment: Investment):
    if investment.status != "active":
        raise ValueError("Investment already withdrawn")

    principal = investment.amount
    interest = Decimal("0.00")

    if investment.is_interest_unlocked():
        interest = calculate_accrued_interest(
        principal=principal,
        start_date=investment.start_date
    )

    total_payout = principal + interest

    debit_wallet(
        wallet=investment.user.wallet,
        amount=total_payout,
        tx_type="withdrawal",
        source="system",
        reference_id=investment.id,
        note="Investment withdrawal",
    )

    investment.status = "withdrawn"
    investment.withdrawn_at = now()
    investment.save(update_fields=["status", "withdrawn_at"])

    return {
        "principal": principal,
        "interest": interest,
        "total": total_payout,
        "days_invested": (now() - investment.start_date).days
    }


import requests
import os
from decimal import Decimal


def get_live_gold_price():
    api_key = os.getenv("GOLD_API_KEY")

    url = "https://www.goldapi.io/api/XAU/INR"

    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    # price per ounce
    price_per_ounce = Decimal(str(data["price"]))

    # convert ounce to gram (1 ounce = 31.1035g)
    price_per_gram = price_per_ounce / Decimal("31.1035")

    return round(price_per_gram, 2)

import requests
from decimal import Decimal
from django.conf import settings
from .models import GoldPrice

GOLDAPI_URL = "https://www.goldapi.io/api/XAU/INR"

def fetch_and_store_gold_price():
    headers = {
        "x-access-token": settings.GOLD_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(GOLDAPI_URL, headers=headers)

    if response.status_code != 200:
        print("Gold API Error:", response.text)
        return

    data = response.json()

    # GoldAPI returns price per ounce
    price_per_ounce = Decimal(str(data["price"]))

    # Convert ounce → gram (1 ounce = 31.1035 grams)
    price_per_gram = price_per_ounce / Decimal("31.1035")

    GoldPrice.objects.create(
        price_per_gram=round(price_per_gram, 2),
        currency="INR"
    )

    print("Gold price updated:", price_per_gram)


from decimal import Decimal
from django.utils import timezone
from wallet.services import credit_wallet, debit_wallet
from wallet.models import Wallet
from .models import GoldInvestment, BondInvestment
from .models import GoldPrice


# ==============================
# GOLD INVESTMENT
# ==============================

def invest_in_gold(user, amount):
    wallet = user.wallet

    if wallet.balance < amount:
        raise ValueError("Insufficient wallet balance")

    latest_price = GoldPrice.objects.order_by("-updated_at").first()
    if not latest_price:
        raise ValueError("Gold price unavailable")

    grams = Decimal(amount) / latest_price.price_per_gram

    debit_wallet(
        wallet=wallet,
        amount=Decimal(amount),
        tx_type="gold_investment",
        source="investment",
        note="Gold Investment"
    )

    return GoldInvestment.objects.create(
        user=user,
        grams=grams,
        buy_price_per_gram=latest_price.price_per_gram,
        total_invested=amount,
    )


def withdraw_gold(user, investment_id):
    investment = GoldInvestment.objects.get(id=investment_id, user=user)

    latest_price = GoldPrice.objects.order_by("-updated_at").first()

    current_value = investment.current_value(latest_price.price_per_gram)

    credit_wallet(
        wallet=user.wallet,
        amount=current_value,
        tx_type="gold_withdrawal",
        source="investment",
        note="Gold Sold"
    )

    investment.is_active = False
    investment.save()

    return current_value


# ==============================
# BOND INVESTMENT
# ==============================

def invest_in_bond(user, amount, roi_percent=8, duration=12):
    wallet = user.wallet

    if wallet.balance < amount:
        raise ValueError("Insufficient wallet balance")

    debit_wallet(
        wallet=wallet,
        amount=Decimal(amount),
        tx_type="bond_investment",
        source="investment",
        note="Bond Investment"
    )

    return BondInvestment.objects.create(
        user=user,
        amount=amount,
        roi_percent=roi_percent,
        duration_months=duration,
    )


def withdraw_bond(user, bond_id):
    bond = BondInvestment.objects.get(id=bond_id, user=user)

    if timezone.now() < bond.maturity_date:
        raise ValueError("Bond not matured yet")

    payout = bond.maturity_amount()

    credit_wallet(
        wallet=user.wallet,
        amount=payout,
        tx_type="bond_withdrawal",
        source="investment",
        note="Bond Maturity"
    )

    bond.is_active = False
    bond.save()

    return payout