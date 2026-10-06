from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils import success_response
from shared.models import FCMToken


class RegisterFCMTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('token', '')
        if not token:
            return Response({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Token kerak'}
            }, status=400)

        FCMToken.objects.update_or_create(
            token=token,
            defaults={'user': request.user}
        )

        return success_response(message='FCM token saqlandi')
