from .models import Notification


def send_notification(*, user, title, message, type="info"):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type,
    )
