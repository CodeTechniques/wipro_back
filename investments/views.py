from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from .models import Investment
from .services import create_investment, withdraw_investment


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def gold_invest(request):
    try:
        amount = Decimal(request.data.get("amount"))
        investment = invest_in_gold(request.user, amount)
        return Response({
            "success": True,
            "grams": float(investment.grams),
            "invested": float(investment.total_invested),
        })
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bond_invest(request):
    try:
        amount = Decimal(request.data.get("amount"))
        bond = invest_in_bond(request.user, amount)
        return Response({
            "success": True,
            "bond_amount": float(bond.amount),
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bond_withdraw(request):
    try:
        bond_id = request.data.get("bond_id")
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
        current_value = g.grams * current_price
        profit = current_value - g.total_invested

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

    bond_data = []

    for b in bond_investments:
        matured = timezone.now() >= b.maturity_date
        maturity_amount = b.maturity_amount()

        bond_data.append({
            "id": b.id,
            "invested_amount": float(b.amount),
            "roi_percent": float(b.roi_percent),
            "maturity_date": b.maturity_date.strftime("%Y-%m-%d"),
            "maturity_amount": float(maturity_amount),
            "is_matured": matured,
            "created_at": b.start_date.strftime("%Y-%m-%d"),
        })

    return Response({
        "gold_investments": gold_data,
        "bond_investments": bond_data,
    })
