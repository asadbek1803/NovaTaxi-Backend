import logging
import random
import string

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

from api.utils import success_response, error_response, calc_distance
from core.sms import send_sms_via_gateway
from api.user.models import OTPCode, RefreshToken, User
from shared.models import Driver, Ride, DriverProfile, Vehicle, FCMToken

from .permissions import IsDriver, IsDriverVerified
from .serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    RegisterDriverSerializer,
    RefreshTokenSerializer,
    FCMTokenSerializer,
    OnboardingSerializer,
    DriverProfileSerializer,
    VehicleSerializer,
    DriverStatusSerializer,
    RideListSerializer,
    RideDetailSerializer,
    RideStatusUpdateSerializer,
    LocationUpdateSerializer,
)

logger = logging.getLogger('api.driver')

# Hujjatdagi status → ichki Ride status
RIDE_STATUS_MAP = {
    'accepted': 'accepted',
    'arrived': 'arriving',
    'arriving': 'arriving',
    'trip_started': 'in_progress',
    'in_progress': 'in_progress',
    'trip_completed': 'completed',
    'completed': 'completed',
    'cancelled': 'cancelled',
}

# Ichki status → hujjatdagi status (WS/client)
RIDE_STATUS_TO_APP = {
    'accepted': 'accepted',
    'arriving': 'arrived',
    'in_progress': 'trip_started',
    'completed': 'trip_completed',
    'cancelled': 'cancelled',
    'pending': 'pending',
}


def format_iso(dt):
    if not dt:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def driver_auth_payload(driver, access_token, refresh_token):
    """Hujjat 1.2 — verify-otp / register javob formati."""
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'driver_id': driver.id,
        'phone_number': driver.phone,
        'status': driver.get_app_status(),
        'full_name': driver.name or None,
        'driver_license': driver.driver_license or None,
        'created_at': format_iso(driver.created_at),
        'rejection_reason': driver.rejection_reason or (
            getattr(getattr(driver.user, 'driver_document', None), 'rejection_reason', None) or None
        ) or None,
    }


def driver_status_payload(driver):
    """Hujjat 2.1 — GET /v1/drivers/status."""
    rejection = driver.rejection_reason or None
    try:
        if driver.user and hasattr(driver.user, 'driver_document'):
            doc = driver.user.driver_document
            if doc and doc.rejection_reason:
                rejection = doc.rejection_reason
    except Exception:
        pass

    return {
        'id': driver.id,
        'phone_number': driver.phone,
        'full_name': driver.name or None,
        'driver_license': driver.driver_license or None,
        'status': driver.get_app_status(),
        'created_at': format_iso(driver.created_at),
        'rejection_reason': rejection or None,
    }


def get_or_create_driver(user, phone, **defaults):
    driver, created = Driver.objects.get_or_create(
        user=user,
        defaults={
            'name': defaults.get('name') or user.full_name or '',
            'phone': phone,
            'car_model': defaults.get('car_model', ''),
            'license_plate': defaults.get('license_plate', ''),
            'car_color': defaults.get('car_color', ''),
            'driver_license': defaults.get('driver_license', ''),
            'is_available': False,
            'is_verified': False,
        },
    )
    if not created and driver.phone != phone:
        driver.phone = phone
        driver.save(update_fields=['phone'])
    return driver, created


def issue_tokens(user):
    jwt_refresh = JWTRefreshToken.for_user(user)
    access_token = str(jwt_refresh.access_token)
    refresh_token = str(jwt_refresh)
    RefreshToken.objects.create(user=user, token=refresh_token)
    return access_token, refresh_token


def doc_error(message, error=None, status_code=400):
    """Hujjatdagi xato formati: {message, error?}."""
    body = {'message': message}
    if error:
        body['error'] = error
    return Response(body, status=status_code)


def build_order_payload(ride):
    """WebSocket new_order formati (hujjat 3.2)."""
    dist = f'{ride.distance_km} km' if ride.distance_km else '0 km'
    eta = f'{ride.duration_min} daqiqa' if ride.duration_min else ''
    return {
        'id': ride.id,
        'pickupAddress': ride.from_address,
        'destinationAddress': ride.to_address,
        'price': ride.price,
        'distance': dist,
        'estimatedTime': eta,
        'pickupLat': ride.from_lat,
        'pickupLng': ride.from_lng,
        'destinationLat': ride.to_lat,
        'destinationLng': ride.to_lng,
    }


def notify_nearby_drivers(ride, radius_km=15):
    """Yangi buyurtmani onlayn haydovchilarga WS orqali yuborish."""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        drivers = Driver.objects.filter(
            is_available=True,
            is_active=True,
            is_verified=True,
        )
        if ride.category_id:
            category_drivers = drivers.filter(category=ride.category) | drivers.filter(category__isnull=True)
            drivers = category_drivers.distinct()

        order = build_order_payload(ride)
        sent = 0
        for driver in drivers:
            if driver.current_lat and driver.current_lng:
                dist = calc_distance(
                    driver.current_lat, driver.current_lng,
                    ride.from_lat, ride.from_lng,
                )
                if dist > radius_km:
                    continue
            async_to_sync(channel_layer.group_send)(
                f'driver_{driver.id}',
                {
                    'type': 'new_order',
                    'order': order,
                },
            )
            sent += 1
        logger.info('Broadcast new_order %s to %s drivers', ride.id, sent)
    except Exception as exc:
        logger.exception('notify_nearby_drivers failed: %s', exc)


# ──────────────────────────────────────────────
# 1. Autentifikatsiya (hujjat bo'limi)
# ──────────────────────────────────────────────

class SendOTPView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            msg = next(iter(serializer.errors.values()))
            if isinstance(msg, list):
                msg = msg[0]
            return doc_error(str(msg), 'VALIDATION_ERROR', 422)

        phone = serializer.validated_data['phone']
        otp_length = getattr(django_settings, 'OTP_LENGTH', 6)
        # Hujjat: 6 xonali kod
        otp_length = max(otp_length, 4)
        code = ''.join(random.choices(string.digits, k=otp_length))

        OTPCode.objects.filter(phone=phone, is_used=False).update(is_used=True)
        OTPCode.objects.create(phone=phone, code=code)

        sms_sent = send_sms_via_gateway(phone, code)

        if not sms_sent:
            if getattr(django_settings, 'DEBUG', False):
                logger.warning('DEBUG mode: SMS yuborilmadi, OTP saqlandi | %s → %s', phone, code)
            else:
                return doc_error(
                    "Tasdiqlash kodini yuborib bo'lmadi. Keyinroq qayta urinib ko'ring.",
                    'SMS_FAILED',
                    503,
                )

        # Hujjat: 200 OK, body shart emas
        return Response(status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            msg = next(iter(serializer.errors.values()))
            if isinstance(msg, list):
                msg = msg[0]
            return doc_error(str(msg), 'VALIDATION_ERROR', 422)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        otp = OTPCode.objects.filter(
            phone=phone, code=code, is_used=False
        ).order_by('-created_at').first()

        if not otp:
            return doc_error("Tasdiqlash kodi noto'g'ri", 'INVALID_OTP', 400)

        otp_age = (timezone.now() - otp.created_at).total_seconds()
        if otp_age > getattr(django_settings, 'OTP_EXPIRY_SECONDS', 120):
            return doc_error("Tasdiqlash kodining muddati tugagan", 'OTP_EXPIRED', 400)

        otp.is_used = True
        otp.save()

        user, is_new = User.objects.get_or_create(phone=phone)
        user.is_driver = True
        user.is_verified = True
        if is_new and not user.full_name:
            user.full_name = ''
        user.save()

        driver, _ = get_or_create_driver(user, phone)
        access_token, refresh_token = issue_tokens(user)

        return Response(
            driver_auth_payload(driver, access_token, refresh_token),
            status=status.HTTP_200_OK,
        )


class RegisterDriverView(APIView):
    """POST /v1/auth/register — yangi haydovchi ro'yxatdan o'tadi."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterDriverSerializer(data=request.data)
        if not serializer.is_valid():
            msg = next(iter(serializer.errors.values()))
            if isinstance(msg, list):
                msg = msg[0]
            return doc_error(str(msg), 'VALIDATION_ERROR', 422)

        data = serializer.validated_data
        phone = data['phone_number']

        user, _ = User.objects.get_or_create(phone=phone)
        user.is_driver = True
        user.is_verified = True
        user.full_name = data['full_name']
        user.save()

        driver, created = Driver.objects.get_or_create(
            user=user,
            defaults={
                'name': data['full_name'],
                'phone': phone,
                'car_model': data['car_model'],
                'car_color': data['car_color'],
                'license_plate': data['license_plate'],
                'driver_license': data['driver_license'],
                'is_available': False,
                'is_verified': False,
            },
        )
        if not created:
            driver.name = data['full_name']
            driver.phone = phone
            driver.car_model = data['car_model']
            driver.car_color = data['car_color']
            driver.license_plate = data['license_plate']
            driver.driver_license = data['driver_license']
            # Yangi ma'lumot yuborilganda rad etishni tozalash
            if driver.rejection_reason:
                driver.rejection_reason = ''
            driver.save()

        profile, _ = DriverProfile.objects.get_or_create(user=user)
        profile.license_number = data['driver_license']
        profile.save()

        vehicle, _ = Vehicle.objects.get_or_create(user=user)
        vehicle.car_model = data['car_model']
        vehicle.car_number = data['license_plate']
        vehicle.car_color = data['car_color']
        vehicle.save()

        access_token, refresh_token = issue_tokens(user)
        return Response(
            driver_auth_payload(driver, access_token, refresh_token),
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return doc_error("Refresh token majburiy", 'VALIDATION_ERROR', 422)

        token_value = serializer.validated_data['refresh_token']
        rt = RefreshToken.objects.filter(token=token_value, is_revoked=False).first()
        if not rt:
            return doc_error("Noto'g'ri refresh token", 'INVALID_TOKEN', 401)

        rt.is_revoked = True
        rt.save()

        access_token, refresh_token = issue_tokens(rt.user)
        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 3600,
        })


class LogoutView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        RefreshToken.objects.filter(user=request.user, is_revoked=False).update(is_revoked=True)
        driver = Driver.objects.filter(user=request.user).first()
        if driver:
            driver.is_available = False
            driver.save(update_fields=['is_available'])
        return success_response(message="Tizimdan muvaffaqiyatli chiqildi")


# ──────────────────────────────────────────────
# 2. Haydovchi profili (hujjat)
# ──────────────────────────────────────────────

class DriverAppStatusView(APIView):
    """GET /v1/drivers/status"""
    permission_classes = [IsDriver]

    def get(self, request):
        driver = Driver.objects.filter(user=request.user).first()
        if not driver:
            return doc_error("Haydovchi profili topilmadi", 'NOT_FOUND', 404)
        return Response(driver_status_payload(driver), status=status.HTTP_200_OK)


class DriverOnboardingDocView(APIView):
    """POST /v1/drivers/onboarding — multipart hujjatlar."""
    permission_classes = [IsDriver]

    def post(self, request):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        # Form maydonlari
        full_name = data.get('full_name', '').strip()
        car_model = data.get('car_model', '').strip()
        car_color = data.get('car_color', '').strip()
        license_plate = data.get('license_plate', '').strip()
        driver_license = data.get('driver_license', '').strip()
        phone_number = (data.get('phone_number') or request.user.phone or '').strip()

        missing = []
        for field, value in [
            ('full_name', full_name),
            ('car_model', car_model),
            ('car_color', car_color),
            ('license_plate', license_plate),
            ('driver_license', driver_license),
        ]:
            if not value:
                missing.append(field)

        passport = request.FILES.get('passport')
        selfie = request.FILES.get('selfie')
        car_photo = request.FILES.get('car_photo')

        for field, file_obj in [
            ('passport', passport),
            ('selfie', selfie),
            ('car_photo', car_photo),
        ]:
            if not file_obj:
                missing.append(field)

        if missing:
            return doc_error(
                f"Majburiy maydonlar: {', '.join(missing)}",
                'VALIDATION_ERROR',
                422,
            )

        # Fayl hajmi (max 5MB)
        max_size = 5 * 1024 * 1024
        for name, f in [('passport', passport), ('selfie', selfie), ('car_photo', car_photo)]:
            if f.size > max_size:
                return doc_error(f"{name} fayli 5MB dan oshmasligi kerak", 'FILE_TOO_LARGE', 400)

        user = request.user
        user.full_name = full_name
        if phone_number and phone_number != user.phone:
            # telefon o'zgartirilmaydi, faqat mos kelishi
            pass
        user.is_driver = True
        user.save()

        driver, _ = get_or_create_driver(
            user, user.phone,
            name=full_name,
            car_model=car_model,
            license_plate=license_plate,
            car_color=car_color,
            driver_license=driver_license,
        )
        driver.name = full_name
        driver.car_model = car_model
        driver.car_color = car_color
        driver.license_plate = license_plate
        driver.driver_license = driver_license
        driver.rejection_reason = ''
        driver.is_verified = False
        driver.is_available = False
        driver.save()

        profile, _ = DriverProfile.objects.get_or_create(user=user)
        profile.license_number = driver_license
        profile.passport = passport
        profile.selfie = selfie
        # license_image sifatida passport saqlash (panel mosligi)
        if not profile.license_image:
            profile.license_image = passport
        profile.is_submitted = True
        profile.is_verified = False
        profile.rejection_reason = ''
        profile.save()

        vehicle, _ = Vehicle.objects.get_or_create(user=user)
        vehicle.car_model = car_model
        vehicle.car_number = license_plate
        vehicle.car_color = car_color
        vehicle.car_photo = car_photo
        vehicle.save()

        # Hujjat: 200 OK, holat pending
        return Response(status=status.HTTP_200_OK)


class DriverFCMTokenView(APIView):
    """POST /v1/drivers/fcm-token"""
    permission_classes = [IsDriver]

    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return doc_error("fcm_token majburiy", 'VALIDATION_ERROR', 422)

        token = serializer.validated_data['fcm_token']
        FCMToken.objects.update_or_create(
            token=token,
            defaults={'user': request.user},
        )
        return Response(status=status.HTTP_200_OK)


# ──────────────────────────────────────────────
# Ichki / kengaytirilgan endpointlar (eski + qo'shimcha)
# ──────────────────────────────────────────────

class DriverOnboardingView(APIView):
    """Eski: /v1/driver/profile/onboarding"""
    permission_classes = [IsDriver]

    def get(self, request):
        profile, _ = DriverProfile.objects.get_or_create(user=request.user)
        vehicle, _ = Vehicle.objects.get_or_create(user=request.user)
        return success_response(data={
            'document': DriverProfileSerializer(profile).data,
            'vehicle': VehicleSerializer(vehicle).data,
        })

    def post(self, request):
        # Agar multipart hujjat formatida bo'lsa — doc view ga yo'naltirish
        if request.FILES.get('passport') or request.FILES.get('selfie'):
            return DriverOnboardingDocView().post(request)

        profile, _ = DriverProfile.objects.get_or_create(user=request.user)
        vehicle, _ = Vehicle.objects.get_or_create(user=request.user)

        doc_data = {}
        for key in ('license_number', 'license_image', 'passport', 'selfie'):
            if key in request.data:
                doc_data[key] = request.data[key]
            if key in request.FILES:
                doc_data[key] = request.FILES[key]

        veh_data = {}
        for key in ('car_model', 'car_number', 'car_color', 'car_photo', 'tech_passport'):
            if key in request.data:
                veh_data[key] = request.data[key]
            if key in request.FILES:
                veh_data[key] = request.FILES[key]

        if doc_data:
            doc_serializer = DriverProfileSerializer(profile, data=doc_data, partial=True)
            doc_serializer.is_valid(raise_exception=True)
            doc_serializer.save()

        if veh_data:
            veh_serializer = VehicleSerializer(vehicle, data=veh_data, partial=True)
            veh_serializer.is_valid(raise_exception=True)
            veh_serializer.save()

        profile.refresh_from_db()
        vehicle.refresh_from_db()

        all_filled = all([
            profile.license_number,
            profile.license_image or profile.passport,
            vehicle.car_model,
            vehicle.car_number,
            vehicle.car_color,
            vehicle.car_photo,
        ])

        profile.is_submitted = all_filled or profile.is_submitted
        if all_filled:
            profile.is_submitted = True
        profile.save()

        driver = Driver.objects.filter(user=request.user).first()
        if driver:
            if vehicle.car_model:
                driver.car_model = vehicle.car_model
            if vehicle.car_number:
                driver.license_plate = vehicle.car_number
            if vehicle.car_color:
                driver.car_color = vehicle.car_color
            if profile.license_number:
                driver.driver_license = profile.license_number
            if request.data.get('full_name'):
                driver.name = request.data['full_name']
                request.user.full_name = request.data['full_name']
                request.user.save(update_fields=['full_name'])
            driver.save()

        return success_response(data={
            'document': DriverProfileSerializer(profile).data,
            'vehicle': VehicleSerializer(vehicle).data,
            'is_submitted': profile.is_submitted,
        })


class DriverStatusView(APIView):
    """Eski: /v1/driver/profile/status — kengaytirilgan ma'lumot."""
    permission_classes = [IsDriver]

    def get(self, request):
        driver = Driver.objects.filter(user=request.user).first()
        if not driver:
            return error_response('NOT_FOUND', "Haydovchi profili topilmadi", 404)

        # Hujjat formatini so'rov parametr orqali ham berish mumkin
        if request.query_params.get('format') == 'app':
            return Response(driver_status_payload(driver))

        data = DriverStatusSerializer(driver).data
        data['app_status'] = driver.get_app_status()
        return success_response(data=data)


class AvailableRidesView(APIView):
    permission_classes = [IsDriverVerified]

    def get(self, request):
        driver = request.user.driver_profile

        try:
            lat = float(request.query_params.get('lat', driver.current_lat or 0))
            lng = float(request.query_params.get('lng', driver.current_lng or 0))
        except (ValueError, TypeError):
            lat = driver.current_lat or 0
            lng = driver.current_lng or 0

        try:
            radius_km = float(request.query_params.get('radius_km', 10))
        except (ValueError, TypeError):
            radius_km = 10

        pending_rides = Ride.objects.filter(
            status='pending',
            driver__isnull=True,
        )

        result = []
        for ride in pending_rides:
            dist = calc_distance(lat, lng, ride.from_lat, ride.from_lng)
            if dist <= radius_km:
                result.append({
                    'ride_id': ride.id,
                    'order': build_order_payload(ride),
                    'passenger_name': ride.passenger.full_name or '',
                    'from_address': ride.from_address,
                    'from_lat': ride.from_lat,
                    'from_lng': ride.from_lng,
                    'to_address': ride.to_address,
                    'to_lat': ride.to_lat,
                    'to_lng': ride.to_lng,
                    'price': ride.price,
                    'currency': ride.currency,
                    'distance_km': ride.distance_km,
                    'duration_min': ride.duration_min,
                    'category': ride.category_id,
                    'distance_to_pickup_km': round(dist, 2),
                })

        result.sort(key=lambda x: x['distance_to_pickup_km'])
        return success_response(data={'rides': result, 'total': len(result)})


class AcceptRideView(APIView):
    permission_classes = [IsDriverVerified]

    def post(self, request, ride_id):
        driver = request.user.driver_profile
        result = accept_ride_for_driver(driver, ride_id)
        if isinstance(result, Response):
            return result
        return success_response(data=RideDetailSerializer(result).data)


def accept_ride_for_driver(driver, ride_id):
    """HTTP va WebSocket uchun umumiy buyurtma qabul qilish."""
    try:
        with transaction.atomic():
            ride = Ride.objects.select_for_update().get(id=ride_id)
            if ride.status != 'pending':
                return error_response(
                    'RIDE_TAKEN',
                    "Sayohat boshqa haydovchi tomonidan qabul qilindi yoki bekor qilindi",
                    409,
                )
            if ride.driver_id and ride.driver_id != driver.id:
                return error_response('RIDE_TAKEN', "Sayohat boshqa haydovchi tomonidan qabul qilindi", 409)

            ride.driver = driver
            ride.status = 'accepted'
            ride.save()
    except Ride.DoesNotExist:
        return error_response('NOT_FOUND', "Sayohat topilmadi", 404)

    driver.is_available = False
    driver.save(update_fields=['is_available'])

    # Yo'lovchi va admin ga xabar
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'ride_{ride.id}_status',
                {
                    'type': 'ride_status',
                    'data': {
                        'type': 'ride_status',
                        'ride_id': ride.id,
                        'status': 'accepted',
                        'driver': {
                            'id': driver.id,
                            'name': driver.name,
                            'phone': driver.phone,
                            'car_model': driver.car_model,
                            'license_plate': driver.license_plate,
                            'lat': driver.current_lat,
                            'lng': driver.current_lng,
                        },
                    },
                },
            )
            async_to_sync(channel_layer.group_send)(
                'admin_drivers',
                {
                    'type': 'driver_status_update',
                    'data': {
                        'id': driver.id,
                        'is_available': False,
                        'active_ride': ride.id,
                    },
                },
            )
    except Exception:
        pass

    return ride


def decline_ride_for_driver(driver, ride_id):
    """Haydovchi buyurtmani rad etadi (boshqalarga ochiq qoladi)."""
    ride = Ride.objects.filter(id=ride_id, status='pending').first()
    if not ride:
        return False
    # Faqat shu haydovchiga bildirish — ride pending qoladi
    return True


def update_ride_status_for_driver(driver, ride_id, app_status, cancel_reason=''):
    """Safar holatini yangilash (HTTP + WS)."""
    internal = RIDE_STATUS_MAP.get(app_status, app_status)

    try:
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except Ride.DoesNotExist:
        return error_response('NOT_FOUND', "Sayohat topilmadi", 404)

    valid_transitions = {
        'accepted': ['arriving', 'cancelled'],
        'arriving': ['in_progress', 'cancelled'],
        'in_progress': ['completed', 'cancelled'],
    }

    allowed = valid_transitions.get(ride.status, [])
    if internal not in allowed:
        return error_response(
            'INVALID_STATUS',
            f"Holat o'zgarishi mumkin emas: {ride.status} -> {internal}",
            400,
        )

    ride.status = internal

    if internal == 'cancelled':
        ride.cancel_reason = cancel_reason or ''
        driver.is_available = True
        driver.save(update_fields=['is_available'])
    elif internal == 'completed':
        ride.completed_at = timezone.now()
        driver.is_available = True
        driver.balance = (driver.balance or 0) + (ride.price or 0)
        driver.save(update_fields=['is_available', 'balance'])
        ride.passenger.total_rides = (ride.passenger.total_rides or 0) + 1
        ride.passenger.save(update_fields=['total_rides'])

    ride.save()

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'ride_{ride.id}_status',
                {
                    'type': 'ride_status',
                    'data': {
                        'type': 'ride_status',
                        'ride_id': ride.id,
                        'order_id': ride.id,
                        'status': RIDE_STATUS_TO_APP.get(internal, internal),
                    },
                },
            )
    except Exception:
        pass

    return ride


class RideStatusView(APIView):
    permission_classes = [IsDriverVerified]

    def post(self, request, ride_id):
        driver = request.user.driver_profile
        serializer = RideStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        cancel_reason = serializer.validated_data.get('cancel_reason', '')

        result = update_ride_status_for_driver(driver, ride_id, new_status, cancel_reason)
        if isinstance(result, Response):
            return result
        return success_response(data=RideDetailSerializer(result).data)


class ActiveRideView(APIView):
    permission_classes = [IsDriverVerified]

    def get(self, request):
        driver = request.user.driver_profile
        active = Ride.objects.filter(
            driver=driver,
            status__in=['accepted', 'arriving', 'in_progress'],
        ).order_by('-created_at').first()

        if not active:
            return success_response(data=None)
        return success_response(data=RideDetailSerializer(active).data)


class RideHistoryView(APIView):
    permission_classes = [IsDriverVerified]

    def get(self, request):
        driver = request.user.driver_profile
        rides = Ride.objects.filter(driver=driver).exclude(status='pending')

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
            'rides': RideListSerializer(page_rides, many=True).data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total_items,
                'per_page': per_page,
            },
        })


class LocationUpdateView(APIView):
    permission_classes = [IsDriverVerified]

    def post(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        driver = request.user.driver_profile
        driver.current_lat = d['lat']
        driver.current_lng = d['lng']
        driver.heading = d.get('heading', 0)
        driver.save(update_fields=['current_lat', 'current_lng', 'heading'])

        try:
            channel_layer = get_channel_layer()
            active_ride = Ride.objects.filter(
                driver=driver,
                status__in=['accepted', 'arriving', 'in_progress'],
            ).select_related('passenger').first()

            ride_data = None
            if active_ride:
                ride_data = {
                    'id': active_ride.id,
                    'passenger_name': active_ride.passenger.full_name or active_ride.passenger.phone,
                    'passenger_id': active_ride.passenger.id,
                    'from_address': active_ride.from_address,
                    'from_lat': active_ride.from_lat,
                    'from_lng': active_ride.from_lng,
                    'status': active_ride.status,
                    'price': active_ride.price,
                    'category': active_ride.category_id,
                }
                async_to_sync(channel_layer.group_send)(
                    f'ride_{active_ride.id}_location',
                    {
                        'type': 'driver_location',
                        'data': {
                            'type': 'driver_location',
                            'lat': driver.current_lat,
                            'lng': driver.current_lng,
                            'heading': driver.heading,
                        },
                    },
                )

            async_to_sync(channel_layer.group_send)(
                'admin_drivers',
                {
                    'type': 'driver_location_update',
                    'data': {
                        'id': driver.id,
                        'name': driver.name,
                        'phone': driver.phone,
                        'current_lat': driver.current_lat,
                        'current_lng': driver.current_lng,
                        'heading': driver.heading,
                        'is_available': driver.is_available,
                        'car_model': driver.car_model,
                        'license_plate': driver.license_plate,
                        'rating': driver.rating,
                        'rides': [ride_data] if ride_data else [],
                    },
                },
            )
        except Exception:
            pass

        return success_response(message="Joylashuv yangilandi")


class ToggleAvailabilityView(APIView):
    permission_classes = [IsDriverVerified]

    def post(self, request):
        driver = request.user.driver_profile

        active_ride = Ride.objects.filter(
            driver=driver,
            status__in=['accepted', 'arriving', 'in_progress'],
        ).exists()

        if active_ride:
            return error_response(
                'ACTIVE_RIDE',
                "Faol sayohat davom etmoqda, mavjudlikni o'zgartirib bo'lmaydi",
                400,
            )

        # Explicit is_available body or toggle
        if 'is_available' in request.data:
            driver.is_available = bool(request.data['is_available'])
        else:
            driver.is_available = not driver.is_available
        driver.save(update_fields=['is_available'])

        return success_response(data={
            'is_available': driver.is_available,
            'status': driver.get_app_status(),
        })


class DriverEarningsView(APIView):
    """Qo'shimcha: haydovchi daromadi."""
    permission_classes = [IsDriverVerified]

    def get(self, request):
        driver = request.user.driver_profile
        completed = Ride.objects.filter(driver=driver, status='completed')
        total_rides = completed.count()
        total_earned = sum(completed.values_list('price', flat=True)) or 0

        today = timezone.now().date()
        today_rides = completed.filter(completed_at__date=today)
        today_earned = sum(today_rides.values_list('price', flat=True)) or 0

        return success_response(data={
            'balance': driver.balance,
            'rating': driver.rating,
            'total_rides': total_rides,
            'total_earned': total_earned,
            'today_rides': today_rides.count(),
            'today_earned': today_earned,
            'currency': 'UZS',
        })
