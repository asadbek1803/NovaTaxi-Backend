from rest_framework import serializers

from shared.models import Driver, Ride, DriverProfile, Vehicle


class SendOTPSerializer(serializers.Serializer):
    """Hujjat: phone_number; eski: phone — ikkalasi ham qabul qilinadi."""
    phone_number = serializers.CharField(max_length=20, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    def validate(self, attrs):
        phone = attrs.get('phone_number') or attrs.get('phone')
        if not phone:
            raise serializers.ValidationError({'phone_number': "Telefon raqami majburiy"})
        phone = phone.strip().replace(' ', '')
        if not phone.startswith('+'):
            if phone.startswith('998'):
                phone = f'+{phone}'
            elif phone.startswith('0'):
                phone = f'+998{phone[1:]}'
            else:
                phone = f'+998{phone}'
        digits = phone[1:] if phone.startswith('+') else phone
        if not digits.isdigit() or len(phone) < 12:
            raise serializers.ValidationError({'phone_number': "Telefon raqami noto'g'ri formatda"})
        if not phone.startswith('+998'):
            raise serializers.ValidationError({
                'phone_number': "Telefon raqami +998 XX XXX XX XX formatida bo'lishi kerak"
            })
        attrs['phone'] = phone
        attrs['phone_number'] = phone
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    """Hujjat: phone_number + otp; eski: phone + code."""
    phone_number = serializers.CharField(max_length=20, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    otp = serializers.CharField(max_length=6, required=False)
    code = serializers.CharField(max_length=6, required=False)

    def validate(self, attrs):
        phone = attrs.get('phone_number') or attrs.get('phone')
        code = attrs.get('otp') or attrs.get('code')
        if not phone:
            raise serializers.ValidationError({'phone_number': "Telefon raqami majburiy"})
        if not code:
            raise serializers.ValidationError({'otp': "OTP kodi majburiy"})
        phone = phone.strip().replace(' ', '')
        if not phone.startswith('+'):
            if phone.startswith('998'):
                phone = f'+{phone}'
            else:
                phone = f'+998{phone}'
        attrs['phone'] = phone
        attrs['phone_number'] = phone
        attrs['code'] = str(code).strip()
        attrs['otp'] = attrs['code']
        return attrs


class RegisterDriverSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    full_name = serializers.CharField(max_length=255)
    car_model = serializers.CharField(max_length=255)
    car_color = serializers.CharField(max_length=50)
    license_plate = serializers.CharField(max_length=20)
    driver_license = serializers.CharField(max_length=50)

    def validate_phone_number(self, value):
        value = value.strip().replace(' ', '')
        if not value.startswith('+'):
            if value.startswith('998'):
                value = f'+{value}'
            else:
                value = f'+998{value}'
        if not value.startswith('+998'):
            raise serializers.ValidationError("Telefon raqami +998 formatida bo'lishi kerak")
        return value


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=500, required=False)
    token = serializers.CharField(max_length=500, required=False)

    def validate(self, attrs):
        token = attrs.get('fcm_token') or attrs.get('token')
        if not token:
            raise serializers.ValidationError({'fcm_token': "FCM token majburiy"})
        attrs['fcm_token'] = token
        return attrs


class OnboardingSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=False)
    full_name = serializers.CharField(max_length=255)
    car_model = serializers.CharField(max_length=255)
    car_color = serializers.CharField(max_length=50)
    license_plate = serializers.CharField(max_length=20)
    driver_license = serializers.CharField(max_length=50)
    passport = serializers.ImageField(required=False)
    selfie = serializers.ImageField(required=False)
    car_photo = serializers.ImageField(required=False)


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            'id', 'license_number', 'license_image', 'passport', 'selfie',
            'is_submitted', 'is_verified', 'rejection_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'is_submitted', 'is_verified', 'rejection_reason',
            'created_at', 'updated_at',
        ]


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'id', 'car_model', 'car_number', 'car_color', 'car_photo',
            'tech_passport', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DriverStatusSerializer(serializers.ModelSerializer):
    document = DriverProfileSerializer(source='user.driver_document', read_only=True)
    vehicle = VehicleSerializer(source='user.vehicle', read_only=True)
    subscription_active = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='name', read_only=True)
    phone_number = serializers.CharField(source='phone', read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'name', 'full_name', 'phone', 'phone_number', 'is_verified', 'rating',
            'subscription_end_date', 'balance', 'is_available', 'status',
            'driver_license', 'car_model', 'car_color', 'license_plate',
            'subscription_active', 'days_until_expiry', 'document', 'vehicle',
            'rejection_reason', 'created_at',
        ]
        read_only_fields = ['id', 'name', 'phone', 'rating', 'balance']

    def get_status(self, obj):
        return obj.get_app_status()

    def get_subscription_active(self, obj):
        if not obj.subscription_end_date:
            return False
        from django.utils import timezone
        return obj.subscription_end_date >= timezone.now().date()

    def get_days_until_expiry(self, obj):
        if not obj.subscription_end_date:
            return 0
        from django.utils import timezone
        delta = obj.subscription_end_date - timezone.now().date()
        return max(0, delta.days)


class DriverAppStatusSerializer(serializers.Serializer):
    """Hujjatdagi GET /v1/drivers/status javob formati."""
    id = serializers.CharField()
    phone_number = serializers.CharField()
    full_name = serializers.CharField(allow_null=True)
    driver_license = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    created_at = serializers.CharField(allow_null=True)
    rejection_reason = serializers.CharField(allow_null=True)


class RideListSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source='passenger.full_name', read_only=True, default='')
    passenger_phone = serializers.CharField(source='passenger.phone', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'passenger_name', 'passenger_phone', 'category_name',
            'from_address', 'from_lat', 'from_lng', 'to_address', 'to_lat', 'to_lng',
            'date', 'time', 'price', 'currency', 'distance_km', 'duration_min',
            'status', 'created_at',
        ]

    def get_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d') if obj.created_at else ''

    def get_time(self, obj):
        return obj.created_at.strftime('%H:%M') if obj.created_at else ''


class RideDetailSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source='passenger.full_name', read_only=True, default='')
    passenger_phone = serializers.CharField(source='passenger.phone', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    route_points = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'passenger_name', 'passenger_phone', 'category_name',
            'from_address', 'from_lat', 'from_lng', 'to_address', 'to_lat', 'to_lng',
            'date', 'time', 'price', 'currency', 'payment_method',
            'distance_km', 'duration_min', 'status', 'route_polyline',
            'route_points', 'created_at', 'completed_at',
        ]
        read_only_fields = fields

    def get_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d') if obj.created_at else ''

    def get_time(self, obj):
        return obj.created_at.strftime('%H:%M') if obj.created_at else ''

    def get_route_points(self, obj):
        return [
            {'lat': obj.from_lat, 'lng': obj.from_lng},
            {'lat': obj.to_lat, 'lng': obj.to_lng},
        ]


class RideStatusUpdateSerializer(serializers.Serializer):
    STATUS_CHOICES = [
        ('accepted', 'Qabul qilindi'),
        ('arrived', 'Yetib keldi'),
        ('arriving', 'Yetib kelyapti'),
        ('trip_started', 'Safar boshlandi'),
        ('in_progress', "Yo'lda"),
        ('trip_completed', 'Safar tugadi'),
        ('completed', 'Tugallandi'),
        ('cancelled', 'Bekor qilindi'),
    ]
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    cancel_reason = serializers.CharField(required=False, default='')


class LocationUpdateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    heading = serializers.FloatField(required=False, default=0)


class DriverEarningsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id', 'balance', 'rating']
        read_only_fields = fields
