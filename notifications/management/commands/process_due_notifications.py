from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from notifications.models import DueNotification
from notifications.models import Notification

class Command(BaseCommand):
    help = "Send due payment notifications automatically"

    def handle(self, *args, **kwargs):
        dues = DueNotification.objects.filter(is_active=True)

        for due in dues:
            should_notify = False

            if not due.last_notified_at:
                should_notify = True
            else:
                next_time = due.last_notified_at + timedelta(
                    minutes=due.repeat_after_minutes
                )
                if now() >= next_time:
                    should_notify = True

            if should_notify:
                Notification.objects.create(
                    user=due.user,
                    title="Payment Due",
                    message=(
                        f"You have a pending payment of ₹{due.amount} "
                        f"for {due.committee.name} ({due.plan.name})"
                    ),
                )

                due.last_notified_at = now()
                due.save(update_fields=["last_notified_at"])

                self.stdout.write(
                    f"Notified {due.user.username} for due ₹{due.amount}"
                )
