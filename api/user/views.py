import random
import string

from django.conf import settings as django_settings
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

from api.utils import success_response, error_response
from core.sms import send_sms_via_gateway
from .models import OTPCode, RefreshToken, User, UserSettings
from .serializers import (
    UserSerializer,
    UserSettingsSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    RefreshTokenSerializer,
)


class SendOTPView(APIView):
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']

        otp_length = getattr(django_settings, 'OTP_LENGTH', 4)
        code = ''.join(random.choices(string.digits, k=otp_length))

        OTPCode.objects.filter(phone=phone, is_used=False).update(is_used=True)
        OTPCode.objects.create(phone=phone, code=code)

        sms_sent = send_sms_via_gateway(phone, code)

        if not sms_sent:
            return error_response(
                'SMS_FAILED',
                'Tasdiqlash kodini yuborib bo\'lmadi. Keyinroq qayta urinib ko\'ring.',
                503,
            )

        return success_response(
            data={
                'expires_in': getattr(django_settings, 'OTP_EXPIRY_SECONDS', 60),
                'message': 'Tasdiqlash kodi yuborildi',
            }
        )


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        otp = OTPCode.objects.filter(
            phone=phone, code=code, is_used=False
        ).order_by('-created_at').first()

        if not otp:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_OTP', 'message': 'Tasdiqlash kodi noto\'g\'ri'}
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_age = (timezone.now() - otp.created_at).total_seconds()
        if otp_age > getattr(django_settings, 'OTP_EXPIRY_SECONDS', 60):
            return Response({
                'success': False,
                'error': {'code': 'OTP_EXPIRED', 'message': 'Tasdiqlash kodining muddati tugagan, yangisini oling'}
            }, status=status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save()

        user, is_new = User.objects.get_or_create(phone=phone)
        if is_new:
            UserSettings.objects.create(user=user)
        if not user.is_verified:
            user.is_verified = True
            user.save()

        jwt_refresh = JWTRefreshToken.for_user(user)
        access_token = str(jwt_refresh.access_token)
        refresh_token = str(jwt_refresh)

        RefreshToken.objects.create(user=user, token=refresh_token)

        return success_response(
            data={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': 3600,
                'user': UserSerializer(user).data,
                'is_new_user': is_new,
            }
        )


class RefreshTokenView(APIView):
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_value = serializer.validated_data['refresh_token']

        rt = RefreshToken.objects.filter(token=token_value, is_revoked=False).first()
        if not rt:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_TOKEN', 'message': 'Noto\'g\'ri refresh token'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        rt.is_revoked = True
        rt.save()

        jwt_refresh = JWTRefreshToken.for_user(rt.user)
        new_access = str(jwt_refresh.access_token)
        new_refresh = str(jwt_refresh)

        RefreshToken.objects.create(user=rt.user, token=new_refresh)

        return success_response(
            data={
                'access_token': new_access,
                'refresh_token': new_refresh,
                'expires_in': 3600,
            }
        )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        RefreshToken.objects.filter(user=request.user, is_revoked=False).update(is_revoked=True)
        return success_response(message='Tizimdan muvaffaqiyatli chiqildi')


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return success_response(data=UserSerializer(request.user).data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data)


class UserSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        return success_response(data=UserSettingsSerializer(settings_obj).data)

    def put(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data)
