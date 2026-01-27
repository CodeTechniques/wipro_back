from django.urls import path
from .views import *

urlpatterns = [
    path("my/", MyNotificationsView.as_view()),
    path("admin/send/", AdminSendNotificationView.as_view()),
    path("notifications/", my_notifications),
    path("due-notifications/", due_notifications),
    path(
        "due-notifications/<int:pk>/dismiss/",
        dismiss_due_notification
    ),
    path(
        "due-notifications/<int:due_id>/response/",
        due_response
    ),
    path("notifications/<int:pk>/read/", mark_notification_read),

     path("committee-dues/", committee_dues),
    path("committee-dues/<int:due_id>/expand/", expand_committee_due),

    path(
        "committee-dues/<int:due_id>/response/",
        committee_due_response,
        name="committee-due-response",
    ),

    path("universal-dues/", universal_dues),
    path("universal-dues/<int:due_id>/response/", universal_due_response),

    
]
