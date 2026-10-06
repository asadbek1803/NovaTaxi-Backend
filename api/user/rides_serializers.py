from rest_framework import serializers

from shared.models import CarCategory, Driver, Ride, SurgePricing


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id', 'name', 'phone', 'rating', 'car_model', 'license_plate',
                  'photo_url', 'current_lat', 'current_lng']


class RideDetailSerializer(serializers.ModelSerializer):
    driver = DriverSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    route_points = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = ['id', 'from_address', 'from_lat', 'from_lng', 'to_address', 'to_lat', 'to_lng',
                  'date', 'time', 'price', 'currency', 'payment_method', 'category_name',
                  'driver', 'distance_km', 'duration_min', 'status', 'rating',
                  'route_polyline', 'route_points', 'created_at', 'completed_at']
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


class RideSerializer(serializers.ModelSerializer):
    driver = DriverSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')

    class Meta:
        model = Ride
        fields = ['id', 'from_address', 'from_lat', 'from_lng', 'to_address', 'to_lat', 'to_lng',
                  'status', 'price', 'currency', 'payment_method', 'distance_km', 'duration_min',
                  'rating', 'driver', 'category_name', 'created_at']
        read_only_fields = ['id', 'status', 'price', 'currency', 'distance_km', 'duration_min',
                            'driver', 'rating', 'created_at']


class RideHistorySerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True, default='')
    driver_id = serializers.CharField(source='driver.id', read_only=True, default='')
    car_model = serializers.CharField(source='driver.car_model', read_only=True, default='')
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = ['id', 'from_address', 'from_lat', 'from_lng', 'to_address', 'to_lat', 'to_lng',
                  'date', 'time', 'price', 'currency', 'payment_method', 'category_name',
                  'driver_name', 'driver_id', 'car_model', 'distance_km', 'duration_min',
                  'status', 'rating']

    def get_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d') if obj.created_at else ''

    def get_time(self, obj):
        return obj.created_at.strftime('%H:%M') if obj.created_at else ''


class RideEstimateSerializer(serializers.Serializer):
    from_lat = serializers.FloatField()
    from_lng = serializers.FloatField()
    to_lat = serializers.FloatField()
    to_lng = serializers.FloatField()
    category_id = serializers.SlugField()


class RideRequestSerializer(serializers.Serializer):
    from_address = serializers.CharField()
    from_lat = serializers.FloatField()
    from_lng = serializers.FloatField()
    to_address = serializers.CharField()
    to_lat = serializers.FloatField()
    to_lng = serializers.FloatField()
    category_id = serializers.SlugField()
    payment_method = serializers.CharField(default='cash')


class RideCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default='')


class RideRateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, default='', allow_blank=True)


class DriverLocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    eta_minutes = serializers.IntegerField()


class SurgePricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgePricing
        fields = ['id', 'name', 'reason', 'multiplier', 'description', 'is_active', 'created_at']
        read_only_fields = ['created_at']
