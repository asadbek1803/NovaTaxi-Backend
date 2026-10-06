from rest_framework import serializers

from .models import User, UserSettings
from shared.models import CarCategory, Location, SavedLocation


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        if not value.startswith('+998'):
            raise serializers.ValidationError("Telefon raqami +998 XX XXX XX XX formatida bo'lishi kerak")
        if len(value) != 13:
            raise serializers.ValidationError("Telefon raqami noto'g'ri formatda")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'avatar_url', 'is_verified', 'rating', 'total_rides', 'created_at']
        read_only_fields = ['id', 'phone', 'is_verified', 'rating', 'total_rides', 'created_at']


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['language', 'notifications_enabled', 'location_sharing', 'dark_mode']


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class CarCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarCategory
        fields = ['id', 'name', 'description', 'base_fare', 'price_per_km', 'price_per_minute',
                  'icon_url', 'estimated_arrival_time', 'is_active', 'is_cargo']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'subtitle', 'lat', 'lng', 'type', 'icon']


class SavedLocationSerializer(serializers.ModelSerializer):
    type_label = serializers.SerializerMethodField()

    class Meta:
        model = SavedLocation
        fields = ['id', 'type', 'type_label', 'name', 'address', 'lat', 'lng']
        read_only_fields = ['id']

    def get_type_label(self, obj):
        return dict(SavedLocation.TYPE_CHOICES).get(obj.type, obj.type)


class SavedLocationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedLocation
        fields = ['type', 'name', 'address', 'lat', 'lng']
