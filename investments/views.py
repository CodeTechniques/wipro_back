from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from .models import Investment, BondProduct, GoldProduct
from .services import create_investment, withdraw_investment
from wallet.services import credit_wallet, debit_wallet

class InvestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = Decimal(request.data.get("amount"))
        investment = create_investment(user=request.user, amount=amount)
        return Response({"message": "Investment successful", "investment_id": investment.id})


class WithdrawInvestmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, investment_id):
        investment = Investment.objects.get(id=investment_id, user=request.user)
        data = withdraw_investment(investment=investment)
        return Response({"message": "Withdrawal successful", **data})


class MyInvestmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        investments = Investment.objects.filter(user=request.user)
        return Response([
            {
                "id": i.id,
                "amount": i.amount,
                "status": i.status,
                "interest_unlocked": i.is_interest_unlocked(),
            }
            for i in investments
        ])


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from .services import (
    invest_in_gold,
    withdraw_gold,
    invest_in_bond,
    withdraw_bond,
)


@api_view(["GET"])
def gold_products(request):
    products = GoldProduct.objects.filter(is_active=True)

    return Response([
        {
            "id": p.id,
            "name": p.name,
            "description":p.description,
            "minimum_amount": float(p.minimum_amount),
            "maximum_amount": float(p.maximum_amount),
        }
        for p in products
    ])

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def gold_invest(request):
    try:
        product_id = request.data.get("product_id")
        amount = Decimal(request.data.get("amount"))

        product = GoldProduct.objects.get(
            id=product_id,
            is_active=True
        )

        if amount < product.minimum_amount:
            return Response(
                {"error": "Amount below minimum limit"},
                status=400
            )

        if amount > product.maximum_amount:
            return Response(
                {"error": "Amount exceeds maximum limit"},
                status=400
            )

        wallet = request.user.wallet

        if wallet.balance < amount:
            return Response(
                {"error": "Insufficient wallet balance"},
                status=400
            )

        # 🔥 Get latest gold price
        latest_price = GoldPrice.objects.order_by("-updated_at").first()
        if not latest_price:
            return Response(
                {"error": "Gold price unavailable"},
                status=400
            )

        grams = amount / latest_price.price_per_gram

        # 🔻 Deduct wallet
        debit_wallet(
            wallet=wallet,
            amount=amount,
            tx_type="gold_investment",
            source="investment",
            note="Gold Investment"
        )

        investment = GoldInvestment.objects.create(
            user=request.user,
            product=product,
            grams=grams,
            buy_price_per_gram=latest_price.price_per_gram,
            total_invested=amount,
        )

        return Response({
            "success": True,
            "product": product.name,
            "grams_purchased": float(grams),
            "price_per_gram": float(latest_price.price_per_gram),
            "total_invested": float(amount),
        })

    except GoldProduct.DoesNotExist:
        return Response({"error": "Gold product not found"}, status=404)

    except Exception as e:
        return Response({"error": str(e)}, status=400)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def gold_withdraw(request):
    try:
        investment_id = request.data.get("investment_id")
        value = withdraw_gold(request.user, investment_id)
        return Response({
            "success": True,
            "credited_amount": float(value),
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
def bond_products(request):
    bonds = BondProduct.objects.filter(is_active=True)

    return Response([
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "roi_percent": float(b.roi_percent),
            "duration_months": b.duration_months,
            "minimum_amount": float(b.minimum_amount),
            "maximum_amount": float(b.maximum_amount),
        }
        for b in bonds
    ])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bond_invest(request):
    try:
        bond_id = request.data.get("product_id")
        amount = Decimal(request.data.get("amount"))
        print(bond_id)
        bond_product = BondProduct.objects.get(
            id=bond_id,
            is_active=True
        )
        print(bond_product,"2")

        if amount < bond_product.minimum_amount:
            return Response({"error": "Amount below minimum limit"}, status=400)

        if amount > bond_product.maximum_amount:
            return Response({"error": "Amount exceeds maximum limit"}, status=400)

        wallet = request.user.wallet

        if wallet.balance < amount:
            return Response(
                {"error": "Insufficient wallet balance"},
                status=400
            )

        # 🔻 Deduct wallet
        debit_wallet(
            wallet=wallet,
            amount=amount,
            tx_type="bond_investment",
            source="investment",
            note="Bond Investment"
        )

        investment = BondInvestment.objects.create(
            user=request.user,
            bond_product=bond_product,
            amount=amount,
        )

        return Response({
            "success": True,
            "bond_name": bond_product.name,
            "invested_amount": float(amount),
            "roi_percent": float(bond_product.roi_percent),
            "maturity_date": investment.maturity_date,
            "maturity_amount": float(investment.maturity_amount()),
        })

    except BondProduct.DoesNotExist:
        return Response({"error": "Bond not found"}, status=404)

    except Exception as e:
        return Response({"error": str(e)}, status=400)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bond_withdraw(request):
    try:
        bond_id = request.data.get("product_id")
        payout = withdraw_bond(request.user, bond_id)
        return Response({
            "success": True,
            "credited_amount": float(payout),
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)



from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import GoldPrice

@api_view(["GET"])
def current_gold_price(request):
    latest = GoldPrice.objects.order_by("-updated_at").first()

    if not latest:
        return Response({"error": "Gold price not available"}, status=404)

    return Response({
        "price_per_gram": float(latest.price_per_gram),
        "currency": latest.currency,
        "updated_at": latest.updated_at,
    })



from .models import GoldInvestment, BondInvestment, GoldPrice
from django.utils import timezone
from decimal import Decimal


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_investments(request):
    user = request.user
    try:    
        latest_gold = GoldPrice.objects.order_by("-updated_at").first()
        current_price = latest_gold.price_per_gram if latest_gold else Decimal("0")

        # ==========================
        # GOLD INVESTMENTS
        # ==========================
        gold_investments = GoldInvestment.objects.filter(
            user=user,
            is_active=True
        )

        gold_data = []

        for g in gold_investments:
            current_value = g.current_value(current_price)
            profit = g.profit_loss(current_price)
            gold_data.append({
                "id": g.id,
                "grams": float(g.grams),
                "buy_price_per_gram": float(g.buy_price_per_gram),
                "invested_amount": float(g.total_invested),
                "current_price_per_gram": float(current_price),
                "current_value": float(current_value),
                "profit_or_loss": float(profit),
                "created_at": g.created_at.strftime("%Y-%m-%d"),
            })

        # ==========================
        # BOND INVESTMENTS
        # ==========================
        bond_investments = BondInvestment.objects.filter(
            user=user,
            is_active=True
        )
        print(bond_investments,"1")

        bond_data = []

        for b in bond_investments:
            matured = timezone.now() >= b.maturity_date
            maturity_amount = b.maturity_amount()

            bond_data.append({
                "id": b.id,
                "product_name": b.bond_product.name,
                "invested_amount": float(b.amount),
                "roi_percent": float(b.bond_product.roi_percent),
                "duration_months": b.bond_product.duration_months,
                "maturity_date": b.maturity_date.strftime("%Y-%m-%d"),
                "maturity_amount": float(maturity_amount),
                "is_matured": matured,
                "created_at": b.start_date.strftime("%Y-%m-%d"),
            })

        return Response({
            "gold_investments": gold_data,
            "bond_investments": bond_data,
        })
    except Exception as e:
        print("ERROR:", str(e))
        return Response({"error": str(e)}, status=500)

