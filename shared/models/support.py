import uuid

from django.db import models


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Ochiq'),
        ('in_progress', 'Ko\'rib chiqilmoqda'),
        ('closed', 'Yopilgan'),
    ]

    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'tkt_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.subject}'
