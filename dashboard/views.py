from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.utils.timezone import now

from wallet.models import WalletTransaction
from investments.models import Investment
from loans.models import Loan
from notifications.models import Notification


class DashboardWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = request.user.wallet
        txs = WalletTransaction.objects.filter(wallet=wallet)[:5]

        return Response({
            "balance": wallet.balance,
            "status": wallet.status,
            "recent_transactions": [
                {
                    "amount": tx.amount,
                    "type": tx.tx_type,
                    "date": tx.created_at
                } for tx in txs
            ]
        })


class DashboardInvestmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        investments = Investment.objects.filter(user=request.user, status="active")
        total = sum(i.amount for i in investments)

        interest_accrued = Decimal("0.00")
        for i in investments:
            days = (now() - i.start_date).days
            if days >= 365:
                interest_accrued += i.amount * Decimal("0.15") * (Decimal(days) / Decimal("365"))

        return Response({
            "active_investments": investments.count(),
            "total_invested": total,
            "interest_accrued": interest_accrued.quantize(Decimal("0.01")),
        })


class DashboardLoanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loan = Loan.objects.filter(user=request.user, status="active").first()

        return Response({
            "has_active_loan": bool(loan),
            "loan_amount": loan.principal if loan else None,
            "tenure": loan.tenure_months if loan else None,
            "status": loan.status if loan else None,
        })


class DashboardNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread = Notification.objects.filter(user=request.user, is_read=False).count()

        return Response({
            "unread_count": unread
        })
