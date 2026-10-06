from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils import success_response, calc_distance
from shared.models import CarCategory, Driver, Ride, SurgePricing
from api.user.rides_serializers import (
    RideCancelSerializer,
    RideDetailSerializer,
    RideEstimateSerializer,
    RideHistorySerializer,
    RideRateSerializer,
    RideRequestSerializer,
    RideSerializer,
)


def get_active_surge_multiplier():
    active = SurgePricing.objects.filter(is_active=True).order_by('-multiplier').first()
    return active.multiplier if active else 1.0


def calculate_price(category, distance, duration):
    base = category.base_fare
    per_km = int(distance * category.price_per_km)
    per_min = int(duration * category.price_per_minute)
    subtotal = base + per_km + per_min
    multiplier = get_active_surge_multiplier()
    final = int(subtotal * multiplier)
    return final, multiplier


class RideEstimateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RideEstimateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        distance = calc_distance(d['from_lat'], d['from_lng'], d['to_lat'], d['to_lng'])
        duration = max(int(distance * 2.5), 5)

        try:
            category = CarCategory.objects.get(id=d['category_id'])
        except CarCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Kategoriya topilmadi'}
            }, status=404)

        price, multiplier = calculate_price(category, distance, duration)

        response_data = {
            'distance_km': round(distance, 2),
            'duration_min': duration,
            'price': price,
            'currency': 'UZS',
            'surge_multiplier': multiplier,
            'base_fare': category.base_fare,
            'price_per_km': category.price_per_km,
            'price_per_minute': category.price_per_minute,
            'category': {
                'id': category.id,
                'name': category.name,
            }
        }

        if multiplier > 1.0:
            surge = SurgePricing.objects.filter(is_active=True).order_by('-multiplier').first()
            response_data['surge_reason'] = surge.reason if surge else ''
            response_data['surge_name'] = surge.name if surge else ''

        return success_response(data=response_data)


class RideRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RideRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        distance = calc_distance(d['from_lat'], d['from_lng'], d['to_lat'], d['to_lng'])
        duration = max(int(distance * 2.5), 5)

        try:
            category = CarCategory.objects.get(id=d['category_id'])
        except CarCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Kategoriya topilmadi'}
            }, status=404)

        price, _ = calculate_price(category, distance, duration)

        # Buyurtma pending holatda yaratiladi — haydovchilar WS orqali qabul qiladi
        ride = Ride.objects.create(
            passenger=request.user,
            driver=None,
            category=category,
            from_address=d['from_address'],
            from_lat=d['from_lat'],
            from_lng=d['from_lng'],
            to_address=d['to_address'],
            to_lat=d['to_lat'],
            to_lng=d['to_lng'],
            price=price,
            currency='UZS',
            payment_method=d.get('payment_method', 'cash'),
            distance_km=round(distance, 2),
            duration_min=duration,
            status='pending',
        )

        # Yaqin atrofdagi onlayn haydovchilarga new_order yuborish
        try:
            from api.driver.views import notify_nearby_drivers
            notify_nearby_drivers(ride)
        except Exception:
            pass

        return success_response(data=RideSerializer(ride).data, status_code=201)


class RideDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            ride = Ride.objects.get(id=pk, passenger=request.user)
        except Ride.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Sayohat topilmadi'}
            }, status=404)
        return success_response(data=RideDetailSerializer(ride).data)


class RideDriverLocationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            ride = Ride.objects.get(id=pk, passenger=request.user)
        except Ride.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Sayohat topilmadi'}
            }, status=404)

        if not ride.driver:
            return success_response(data={'lat': 0, 'lng': 0, 'eta_minutes': 0})

        return success_response(data={
            'lat': ride.driver.current_lat,
            'lng': ride.driver.current_lng,
            'eta_minutes': ride.category.estimated_arrival_time if ride.category else 5,
        })


class RideCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            ride = Ride.objects.get(id=pk, passenger=request.user)
        except Ride.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Sayohat topilmadi'}
            }, status=404)

        if ride.status in ('completed', 'cancelled'):
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Sayohat allaqachon tugallangan yoki bekor qilingan'}
            }, status=400)

        serializer = RideCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ride.status = 'cancelled'
        ride.cancel_reason = serializer.validated_data.get('reason', '')
        ride.save()

        # Haydovchiga bekor qilish xabari
        if ride.driver_id:
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f'driver_{ride.driver_id}',
                        {
                            'type': 'order_cancelled',
                            'order_id': ride.id,
                            'message': 'Yo\'lovchi buyurtmani bekor qildi',
                        },
                    )
                ride.driver.is_available = True
                ride.driver.save(update_fields=['is_available'])
            except Exception:
                pass

        return success_response(data=RideSerializer(ride).data)


class RideRateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            ride = Ride.objects.get(id=pk, passenger=request.user, status='completed')
        except Ride.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Sayohat topilmadi'}
            }, status=404)

        if ride.rating is not None:
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_RATED', 'message': 'Sayohat allaqachon baholangan'}
            }, status=409)

        serializer = RideRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ride.rating = serializer.validated_data['rating']
        ride.rating_comment = serializer.validated_data.get('comment', '')
        ride.save()

        return success_response(message='Baholashingiz uchun rahmat!')


class RideHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rides = Ride.objects.filter(passenger=request.user).exclude(status='pending')

        status_filter = request.query_params.get('status', 'all')
        if status_filter == 'completed':
            rides = rides.filter(status='completed')
        elif status_filter == 'cancelled':
            rides = rides.filter(status='cancelled')

        total_items = rides.count()

        try:
            page = int(request.query_params.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = int(request.query_params.get('limit', 20))
        except (ValueError, TypeError):
            per_page = 20

        total_pages = max(1, -(-total_items // per_page))
        start = (page - 1) * per_page
        page_rides = rides[start:start + per_page]

        return success_response(data={
            'rides': RideHistorySerializer(page_rides, many=True).data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total_items,
                'per_page': per_page,
            }
        })


class NearbyDriversView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            lat = float(request.query_params.get('lat', 0))
            lng = float(request.query_params.get('lng', 0))
        except (ValueError, TypeError):
            return success_response(data=[])

        try:
            radius_km = float(request.query_params.get('radius_km', 10))
        except (ValueError, TypeError):
            radius_km = 10

        category_id = request.query_params.get('category', None)

        drivers = Driver.objects.filter(is_available=True, is_active=True)
        if category_id:
            drivers = drivers.filter(category_id=category_id)

        result = []
        for d in drivers:
            dist = calc_distance(lat, lng, d.current_lat, d.current_lng)
            if dist <= radius_km:
                result.append({
                    'driver_id': d.id,
                    'name': d.name,
                    'lat': d.current_lat,
                    'lng': d.current_lng,
                    'heading': 0,
                    'category': d.category_id,
                    'car_model': d.car_model,
                    'license_plate': d.license_plate,
                    'is_available': d.is_available,
                })

        return success_response(data=result)
