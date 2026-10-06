import uuid

from django.db import models


class DriverProfile(models.Model):
    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.OneToOneField('api_user.User', on_delete=models.CASCADE, related_name='driver_document')
    license_number = models.CharField(max_length=50, blank=True, default='')
    license_image = models.ImageField(upload_to='driver_docs/license/', blank=True, null=True)
    passport = models.ImageField(upload_to='driver_docs/passport/', blank=True, null=True)
    selfie = models.ImageField(upload_to='driver_docs/selfie/', blank=True, null=True)
    is_submitted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'driver_profiles'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'dp_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'DriverProfile {self.user.phone}'


class Vehicle(models.Model):
    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    user = models.OneToOneField('api_user.User', on_delete=models.CASCADE, related_name='vehicle')
    car_model = models.CharField(max_length=255, blank=True, default='')
    car_number = models.CharField(max_length=20, blank=True, default='')
    car_color = models.CharField(max_length=50, blank=True, default='')
    car_photo = models.ImageField(upload_to='driver_docs/vehicle/', blank=True, null=True)
    tech_passport = models.ImageField(upload_to='driver_docs/tech_passport/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicles'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'veh_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.car_model} {self.car_number}'
