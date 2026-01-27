# notifications/management/commands/send_due_notifications.py
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from notifications.models import DueNotification
from notifications.models import Notification

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        dues = DueNotification.objects.filter(is_active=True)

        for due in dues:
            if (
                not due.last_notified_at or
                now() >= due.last_notified_at + timedelta(minutes=due.repeat_after_minutes)
            ):
                Notification.objects.create(
                    user=due.user,
                    title="Payment Due",
                    message=(
                        f"You have a pending payment of ₹{due.amount} "
                        f"for {due.committee.name} ({due.plan.name})."
                    ),
                )

                due.last_notified_at = now()
                due.save(update_fields=["last_notified_at"])
