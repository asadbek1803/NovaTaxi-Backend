import uuid

from django.db import models


class Region(models.Model):
    id = models.CharField(max_length=30, primary_key=True, default='', editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'regions'

    def __str__(self):
        return self.name


class District(models.Model):
    id = models.CharField(max_length=30, primary_key=True, default='', editable=False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = 'districts'

    def __str__(self):
        return f"{self.name} ({self.region.name})"


class Mfy(models.Model):
    TYPE_CHOICES = [('shahar', 'Shahar'), ('qishloq', 'Qishloq')]
    id = models.CharField(max_length=40, primary_key=True, default='', editable=False)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='mfys')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='shahar')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = 'mfys'
        verbose_name = 'MFY'
        verbose_name_plural = 'MFYlar'

    def __str__(self):
        return f"{self.name} ({self.district.name})"


class Street(models.Model):
    id = models.CharField(max_length=40, primary_key=True, default='', editable=False)
    mfy = models.ForeignKey(Mfy, on_delete=models.CASCADE, related_name='streets')
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = 'streets'

    def __str__(self):
        return f"{self.name} ({self.mfy.name})"


class Location(models.Model):
    TYPE_CHOICES = [
        ('market', 'Bozor'),
        ('mall', 'Savdo markazi'),
        ('transport', 'Transport'),
        ('park', 'Bog\''),
        ('sports', 'Sport'),
        ('education', 'Ta\'lim'),
        ('other', 'Boshqa'),
    ]

    id = models.CharField(max_length=30, primary_key=True, default='', editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField()
    subtitle = models.CharField(max_length=255, blank=True, default='')
    lat = models.FloatField()
    lng = models.FloatField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    icon = models.CharField(max_length=50, default='location_on')

    class Meta:
        db_table = 'locations'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'loc_{uuid.uuid4().hex[:10]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SavedLocation(models.Model):
    TYPE_CHOICES = [
        ('home', 'Uy'),
        ('work', 'Ish'),
        ('favorite', 'Sevimli'),
    ]

    id = models.CharField(max_length=30, primary_key=True, default='', editable=False)
    user = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='saved_locations')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255)
    address = models.TextField()
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        db_table = 'saved_locations'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'sloc_{uuid.uuid4().hex[:10]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.user.phone})'
