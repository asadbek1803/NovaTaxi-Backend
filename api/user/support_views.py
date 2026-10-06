from rest_framework import permissions
from rest_framework.views import APIView

from api.utils import success_response
from shared.models import SupportTicket
from api.user.support_serializers import SupportTicketCreateSerializer, SupportTicketSerializer


class SupportTicketView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=serializer.validated_data['subject'],
            message=serializer.validated_data['message'],
        )

        return success_response(
            data=SupportTicketSerializer(ticket).data,
            status_code=201,
            message='Xabar yuborildi'
        )
