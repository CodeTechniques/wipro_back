from django.urls import path
from . import views
from .views import *

urlpatterns = [
    # Property CRUD
    path('', views.PropertyListCreateView.as_view(), name='property-list-create'),

    # ✅ CORRECT
path("<uuid:property_id>/group-request/", CreateGroupPurchaseView.as_view(), name="group-purchase-request"),

path(
    "group-payment-invites/<uuid:invite_id>/respond/",
    RespondGroupPaymentInviteView.as_view(),
),

path(
    "plans/<uuid:plan_id>/initiate-group-payment/",
    InitiateGroupPaymentView.as_view(),
),

path("users/search/", UserSearchView.as_view()),

path("plans/<uuid:plan_id>/invite-user/", SendGroupPaymentInviteView.as_view()),



    
    path('my-properties/', views.MyPropertiesView.as_view(), name='my-properties'),
    
    # Property Images
    path('<uuid:property_id>/images/', views.PropertyImageUploadView.as_view(), name='property-image-upload'),
    
    # Inquiries
    path('<uuid:property_id>/inquire/', views.PropertyInquiryView.as_view(), name='property-inquire'),
    path('inquiries/sent/', views.MyInquiriesView.as_view(), name='my-inquiries'),
    path('inquiries/received/', views.PropertyInquiriesReceivedView.as_view(), name='inquiries-received'),
    
    # Favorites
    path('<uuid:property_id>/favorite/', views.toggle_favorite, name='toggle-favorite'),
    path('favorites/', views.FavoritePropertiesView.as_view(), name='favorite-properties'),
    
    # Statistics
    path('stats/', views.property_stats, name='property-stats'),



    path(
  "plans/<uuid:plan_id>/share-invite/",
  CreateShareInviteView.as_view()
),



path(
        "<uuid:property_id>/request/",
        CreatePropertyRequestView.as_view(),
        name="create-property-request"
    ),
    path(
        "property-requests/my/",
        MyPropertyRequestsView.as_view(),
        name="my-property-requests"
    ),




    path(
        "properties/<uuid:property_id>/images/upload/",
        PropertyImageUploadView.as_view(),
        name="property-image-upload"
    ),


path(
    "property-images/<int:pk>/",
    PropertyImageDeleteView.as_view(),
    name="property-image-delete"
),


path(
    "<uuid:property_id>/images/",
    PropertyImageUploadView.as_view(),
    name="property-image-upload"
),

    

    # Interest + owner respond
path('<uuid:property_id>/interest/', views.CreateInterestView.as_view(), name='property-interest'),
path('interests/received/', views.InterestsReceivedView.as_view(), name='interests-received'),
path('interests/<uuid:interest_id>/respond/', views.RespondInterestView.as_view(), name='interest-respond'),

# Lead investor transaction
path('<uuid:property_id>/invest/', views.LeadInvestorTransactionView.as_view(), name='lead-invest'),
path("plans/<uuid:plan_id>/payable/", views.PlanPayableView.as_view(), name="plan-payable"),
path("plans/<uuid:plan_id>/pay/", views.PlanPayView.as_view(), name="plan-pay"),


# users/urls.py
path("users/", UserListView.as_view()),


# History + notifications
path('transactions/my/', views.MyTransactionsView.as_view(), name='my-transactions'),
path('notifications/my/', views.MyNotificationsView.as_view(), name='my-notifications'),
# urls.py
path(
    "interests/mine/",
    views.MyInterestsView.as_view(),
    name="interests-mine"
),

path(
    "group-invites/",
    MyGroupPaymentInvitesView.as_view(),
    name="group-invites"
),


# 🔥 DELETE PROPERTY
path(
    "<uuid:property_id>/delete/",
    DeletePropertyView.as_view(),
    name="delete-property"
),


path('<uuid:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),



# 🔹 PROPERTY LISTING REQUEST
path(
    "<uuid:property_id>/request-listing/",
    CreatePropertyListingRequestView.as_view(),
    name="request-property-listing"
),

path(
    "listing-requests/my/",
    MyListingRequestsView.as_view(),
    name="my-listing-requests"
),

path(
    "listing-requests/<uuid:request_id>/pay/",
    ListingPaymentView.as_view(),
    name="listing-payment"
),

]