from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal

from .models import *
from .services import *
from wallet.models import PaymentTransaction



def calculate_loan(principal, interest_percent, duration_months, emi_interval):
    principal = Decimal(principal)
    interest_percent = Decimal(interest_percent)

    interest = (principal * interest_percent * duration_months) / Decimal(100)
    total = principal + interest

    total_emis = duration_months // emi_interval
    emi_amount = total / total_emis

    return {
        "total_interest": round(interest, 2),
        "total_payable": round(total, 2),
        "emi_amount": round(emi_amount, 2),
        "total_emis": total_emis,
    }





class ApplyLoanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        loan_id = request.data.get("loan_id")

        if not loan_id:
            return Response(
                {"error": "loan_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get loan offer (admin-created loan)
        loan = Loan.objects.get(id=loan_id)

        # Get active committee of user
        committee = UserCommittee.objects.filter(
            user=user,
            is_active=True
        ).order_by("-joined_at").first()

        if not committee:
            return Response(
                {"error": "You must be active in a committee"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Prevent duplicate application
        if LoanApplication.objects.filter(user=user, committee=committee, status="pending").exists():
            return Response(
                {"error": "You already have a pending loan application"},
                status=status.HTTP_400_BAD_REQUEST
            )

        LoanApplication.objects.create(
            user=user,
            committee=committee,
            requested_amount=loan.principal_amount,
            requested_duration_months=loan.duration_months,
            status="pending"
        )

        return Response(
            {"message": "Loan application sent to admin"},
            status=status.HTTP_201_CREATED
        )



class LoanEligibilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        eligible = check_loan_eligibility(user)

        if eligible:
            return Response({
                "eligible": True,
                "message": "You are eligible to apply for a loan"
            })

        return Response({
            "eligible": False,
            "message": "You must be active in a committee for at least 6 months"
        })



class ApproveLoanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, application_id):
        interest_percent = request.data.get("interest_percent")
        emi_interval = request.data.get("emi_interval")

        if not interest_percent or not emi_interval:
            return Response(
                {"error": "interest_percent and emi_interval are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            loan = approve_loan(
                application_id=application_id,
                interest_percent=Decimal(interest_percent),
                emi_interval=int(emi_interval),
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Loan approved successfully",
                "loan_id": loan.id
            },
            status=status.HTTP_200_OK
        )




class MyLoansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loans = Loan.objects.filter(user=request.user)

        data = []
        for loan in loans:
            data.append({
                "id": loan.id,
                "principal_amount": loan.principal_amount,
                "interest_percent": loan.interest_percent,
                "duration_months": loan.duration_months,
                "emi_interval_months": loan.emi_interval_months,
                "emi_amount": loan.emi_amount,
                "total_payable": loan.total_payable,
                "status": loan.status,
            })

        return Response(data)






class MyLoanApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app = LoanApplication.objects.filter(user=request.user).last()

        if not app:
            return Response({"exists": False})

        return Response({
            "exists": True,
            "status": app.status,
            "message": app.admin_message
        })




class LoanWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loan = Loan.objects.filter(user=request.user, status="active").first()
        if not loan:
            return Response({"has_loan": False})

        paid = LoanDue.objects.filter(
            loan=loan, status="paid"
        ).aggregate(total=models.Sum("due_amount"))["total"] or 0

        next_due = LoanDue.objects.filter(
            loan=loan, status="pending"
        ).order_by("due_date").first()

        return Response({
            "has_loan": True,
            "total_loan": loan.total_payable,
            "paid_so_far": paid,
            "emi_due": next_due.due_amount if next_due else 0,
        })




from django.db.models import Sum
from datetime import date

class LoanEligibilityDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get active committee
        committee = UserCommittee.objects.filter(
            user=user,
            is_active=True
        ).order_by("-joined_at").first()

        if not committee:
            return Response({
                "eligible": False,
                "message": "You are not part of any active committee"
            })

        # 🔹 Months completed
        today = date.today()
        months_completed = (
            (today.year - committee.joined_at.year) * 12
            + (today.month - committee.joined_at.month)
        )

        # 🔹 Total invested (REAL data)
        total_invested = PaymentTransaction.objects.filter(
            user=user,
             user_committee=committee,
            status="approved",
            transaction_type="investment"
        ).aggregate(total=Sum("amount"))["total"] or 0

        # 🔹 Admin rule: eligible loan = 2x investment
        eligible_loan_amount = total_invested * 2

        # 🔹 EMI preview (12 months – display only)
        emi_12_months = eligible_loan_amount // 12 if eligible_loan_amount else 0

        eligible = months_completed >= 6

        return Response({
            "monthly_investment": None,  # optional (you don’t truly have this)
            "months_completed": months_completed,
            "total_invested": total_invested,
            "eligible_loan_amount": eligible_loan_amount,
            "emi_12_months": emi_12_months,
            "eligible": eligible,
            "message": (
                f"You are eligible for a loan! Based on your investment, you can apply for up to ₹{eligible_loan_amount}"
                if eligible
                else "You must be active in a committee for at least 6 months"
            )
        })





class LoanDashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loans = Loan.objects.filter(status="active")

        data = []
        for loan in loans:
            data.append({
                "id": loan.id,
                "principal_amount": loan.principal_amount,
                "interest_percent": loan.interest_percent,
                "duration_months": loan.duration_months,
                "emi_amount": loan.emi_amount,
                "status": loan.status,
            })

        return Response(data)








class UserLoanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_loan = UserLoan.objects.filter(user=request.user).first()

        if not user_loan:
            return Response({"has_loan": False})

        return Response({
            "has_loan": True,
            "loan_amount": user_loan.loan_amount,
            "amount_paid": user_loan.amount_paid,
            "emi_amount": user_loan.emi_amount,
            "remaining_amount": user_loan.remaining_amount,
        })






class LoanEmiListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loan = Loan.objects.filter(user=request.user, status="active").first()
        if not loan:
            return Response({"has_loan": False})

        emis = LoanDue.objects.filter(
            loan=loan,
            is_visible=True   # 🔥 IMPORTANT
        ).order_by("due_date")

        data = []
        for emi in emis:
            data.append({
                "id": emi.id,
                "amount": emi.due_amount,
                "due_date": emi.due_date,
                "status": emi.status,
            })

        return Response({
            "has_loan": True,
            "emis": data
        })
