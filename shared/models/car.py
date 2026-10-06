from django.db import models


class CarCategory(models.Model):
    id = models.SlugField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    base_fare = models.IntegerField(default=0)
    price_per_km = models.IntegerField(default=0)
    price_per_minute = models.IntegerField(default=0)
    estimated_arrival_time = models.IntegerField(default=5)
    icon_url = models.URLField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_cargo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'car_categories'
        ordering = ['base_fare']

    def __str__(self):
        return self.name


class SurgePricing(models.Model):
    REASON_CHOICES = [
        ('weather', 'Ob-havo'),
        ('traffic', 'Tirbandlik'),
        ('demand', 'Yuqori talab'),
        ('night', 'Tungi tarif'),
        ('holiday', 'Bayram'),
        ('custom', 'Boshqa'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='custom')
    multiplier = models.FloatField(default=1.0)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'surge_pricing'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.multiplier}x)'
