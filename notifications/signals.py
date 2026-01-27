# notifications/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from committees.models import UserCommittee
from .models import CommitteePaymentDue, DueNotification

@receiver(post_save, sender=CommitteePaymentDue)
def create_due_for_committee_users(sender, instance, created, **kwargs):
    if not created or not instance.is_active:
        return

    users = UserCommittee.objects.filter(
        committee=instance.committee,
        is_active=True
    ).select_related("user")

    for uc in users:
        DueNotification.objects.create(
            user=uc.user,
            committee=instance.committee,
            plan=instance.plan,
            amount=instance.amount,
            repeat_after_minutes=instance.repeat_after_minutes,
            is_active=True,
        )
