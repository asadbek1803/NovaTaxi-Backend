import uuid

from django.db import models


class PaymentMethod(models.Model):
    TYPE_CHOICES = [
        ('uzcard', 'UzCard'),
        ('humo', 'Humo'),
        ('visa', 'Visa'),
        ('mastercard', 'MasterCard'),
    ]

    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    card_number = models.CharField(max_length=20)
    holder_name = models.CharField(max_length=255)
    expiry = models.CharField(max_length=5)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_methods'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'pm_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    @property
    def masked_number(self):
        return f'**** **** **** {self.card_number[-4:]}'

    @property
    def type_label(self):
        return dict(self.TYPE_CHOICES).get(self.type, self.type)

    def __str__(self):
        return f'{self.type_label} {self.masked_number}'
