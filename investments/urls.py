from django.urls import path
from .views import *

urlpatterns = [
    path("invest/", InvestView.as_view()),
    path("withdraw/<uuid:investment_id>/", WithdrawInvestmentView.as_view()),
    path("mine/", MyInvestmentsView.as_view()),
    

    path("gold/products/", gold_products),
    path("gold/invest/", gold_invest),
    path("gold/withdraw/", gold_withdraw),

    path("bond/products/", bond_products),
    path("bond/invest/", bond_invest),
    path("bond/withdraw/", bond_withdraw),
    path("gold-price/", current_gold_price),
    

    path("my-investments/", my_investments),

]
