import uuid

from django.db import models


class Notification(models.Model):
    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'notif_{uuid.uuid4().hex[:10]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ScheduledNotification(models.Model):
    TARGET_CHOICES = [
        ('all', 'Barcha foydalanuvchilar'),
        ('drivers', 'Faqat haydovchilar'),
        ('passengers', 'Faqat yo\'lovchilar'),
    ]
    FREQUENCY_CHOICES = [
        ('daily', 'Har kuni'),
        ('weekly', 'Haftada bir marta'),
        ('weekdays', 'Ish kunlari (Dush-Juma)'),
    ]

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    send_time = models.TimeField(default='09:00')
    days_of_week = models.JSONField(default=list, blank=True,
        help_text='For weekly: [0=Mon, 1=Tue, ... 6=Sun]. Empty = every day for daily.')
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scheduled_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.get_frequency_display()} @ {self.send_time})'

    def should_send_today(self, today=None):
        if not self.is_active:
            return False
        if today is None:
            from django.utils import timezone
            today = timezone.now().date()
        if self.frequency == 'daily':
            return True
        elif self.frequency == 'weekdays':
            return today.weekday() < 5
        elif self.frequency == 'weekly':
            return today.weekday() in (self.days_of_week or [])
        return False


class FCMToken(models.Model):
    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fcm_tokens'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'fcm_{uuid.uuid4().hex[:10]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'FCM for {self.user.phone}'
