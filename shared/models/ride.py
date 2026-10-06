import uuid

from django.db import models


class Driver(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'

    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.OneToOneField('api_user.User', on_delete=models.CASCADE, null=True, blank=True, related_name='driver_profile')
    name = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=20, unique=True)
    rating = models.FloatField(default=5.0)
    car_model = models.CharField(max_length=255, blank=True, default='')
    license_plate = models.CharField(max_length=20, blank=True, default='')
    car_color = models.CharField(max_length=50, blank=True, default='')
    driver_license = models.CharField(max_length=50, blank=True, default='')
    photo_url = models.URLField(max_length=500, blank=True, null=True)
    current_lat = models.FloatField(default=0)
    current_lng = models.FloatField(default=0)
    heading = models.FloatField(default=0)
    is_available = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_cargo = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, default='')
    subscription_end_date = models.DateField(null=True, blank=True)
    balance = models.IntegerField(default=0)
    category = models.ForeignKey('shared.CarCategory', on_delete=models.SET_NULL, null=True, related_name='drivers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'drivers'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'drv_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def get_app_status(self):
        """Haydovchi ilovasi uchun holat: pending/approved/rejected/active/inactive."""
        if self.rejection_reason and not self.is_verified:
            return self.STATUS_REJECTED
        try:
            doc = self.user.driver_document if self.user_id else None
        except Exception:
            doc = None
        if doc and doc.rejection_reason and not doc.is_verified and not self.is_verified:
            return self.STATUS_REJECTED
        if not self.is_verified:
            return self.STATUS_PENDING
        if not self.is_active:
            return self.STATUS_INACTIVE
        if self.is_available:
            return self.STATUS_ACTIVE
        return self.STATUS_APPROVED

    def __str__(self):
        return f'{self.name or self.phone} - {self.car_model or "N/A"}'


class Ride(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('accepted', 'Qabul qilindi'),
        ('arriving', 'Yetib kelyapti'),
        ('in_progress', 'Yo\'lda'),
        ('completed', 'Tugallandi'),
        ('cancelled', 'Bekor qilindi'),
    ]

    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    passenger = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='rides')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides')
    category = models.ForeignKey('shared.CarCategory', on_delete=models.SET_NULL, null=True)

    from_address = models.TextField()
    from_lat = models.FloatField()
    from_lng = models.FloatField()
    to_address = models.TextField()
    to_lat = models.FloatField()
    to_lng = models.FloatField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    price = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, default='UZS')
    payment_method = models.CharField(max_length=50, default='cash')
    distance_km = models.FloatField(default=0)
    duration_min = models.IntegerField(default=0)
    rating = models.IntegerField(null=True, blank=True)
    rating_comment = models.TextField(blank=True, default='')
    cancel_reason = models.TextField(blank=True, default='')
    route_polyline = models.TextField(blank=True, default='')
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rides'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'ride_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.passenger.phone} - {self.status}'
