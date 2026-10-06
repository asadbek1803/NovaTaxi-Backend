import logging
from datetime import time as dt_time

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.user.models import User
from shared.models import Notification, FCMToken, ScheduledNotification
from core.fcm import send_push_notification

logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = 'Send scheduled notifications that are due right now'

    def handle(self, *args, **options):
        now = timezone.localtime()
        today = now.date()
        current_time = now.time()
        scheduled = ScheduledNotification.objects.filter(is_active=True)

        sent_count = 0
        for sched in scheduled:
            if not sched.should_send_today(today):
                continue

            sched_time = sched.send_time
            time_diff_minutes = (
                current_time.hour * 60 + current_time.minute
            ) - (sched_time.hour * 60 + sched_time.minute)

            if time_diff_minutes < 0 or time_diff_minutes > 5:
                continue

            if sched.last_sent_at and sched.last_sent_at.date() == today:
                continue

            self._send_notification(sched)
            sched.last_sent_at = timezone.now()
            sched.save(update_fields=['last_sent_at'])
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f'Scheduled notifications processed: {sent_count} sent'))

    def _send_notification(self, sched):
        users = User.objects.filter(is_active=True)
        if sched.target == 'drivers':
            users = users.filter(is_driver=True)
        elif sched.target == 'passengers':
            users = users.filter(is_driver=False)

        user_ids = list(users.values_list('id', flat=True))

        created_count = 0
        for uid in user_ids:
            Notification.objects.create(
                user_id=uid,
                title=sched.title,
                body=sched.body,
                data={'type': 'scheduled', 'scheduled_id': sched.id, 'target': sched.target}
            )
            created_count += 1

        fcm_tokens = list(
            FCMToken.objects.filter(user_id__in=user_ids).values_list('token', flat=True)
        )

        push_result = {'success': 0, 'failed': 0}
        if fcm_tokens:
            push_result = send_push_notification(
                tokens=fcm_tokens,
                title=sched.title,
                body=sched.body,
                data={'type': 'scheduled', 'scheduled_id': str(sched.id), 'target': sched.target}
            )

        logger.info(
            f"Scheduled '{sched.title}': {created_count} DB, "
            f"{push_result['success']} push, {push_result['failed']} failed"
        )
        self.stdout.write(
            f"  -> {sched.title}: {created_count} DB, "
            f"{push_result['success']} push sent"
        )
