from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils import success_response


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Ruxsat yo\'q'}
            }, status=403)

        return success_response(data={
            'message': 'Admin API tez orada qo\'shiladi',
            'endpoints': [
                'GET /admin/dashboard',
                'GET /admin/users',
                'GET /admin/drivers',
                'POST /admin/drivers/{id}/approve',
                'POST /admin/drivers/{id}/reject',
                'GET /admin/rides',
                'GET /admin/rides/stats',
                'GET /admin/support/tickets',
                'PUT /admin/support/tickets/{id}',
            ]
        })
