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
