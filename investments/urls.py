from django.urls import path
from .views import *

urlpatterns = [
    path("invest/", InvestView.as_view()),
    path("withdraw/<uuid:investment_id>/", WithdrawInvestmentView.as_view()),
    path("mine/", MyInvestmentsView.as_view()),
]
