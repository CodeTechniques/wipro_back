from django.urls import path
from .views import *

urlpatterns = [
   path("committees/", committee_list, name="committee-list"),
   path("committees/<int:committee_id>/join/", join_committee, name="join-committee"),
   path("my-committees/", my_committees),   # 👈 NEW
   path(
        "committee-detail/<int:user_committee_id>/",
        committee_detail,
        name="committee-detail"
    ),

    path("committee-plans/<committee_id>/", committee_plans, name="payment-plan-list"),  # NEW

    path("subscribe-plan/", subscribe_plan, name="subscribe-plan"),  # NEW

    path("pending-payments/<user_committee_id>/", pending_payments, name="pending-payments"),  # NEW
    path("my-due-payments/", my_due_payments),
    path(
    "pay-due/<int:user_committee_id>/",
    pay_due,
    name="pay-due"
),

]

