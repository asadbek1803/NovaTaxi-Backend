from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils import success_response
from shared.models import PaymentMethod
from api.user.payments_serializers import PaymentMethodCreateSerializer, PaymentMethodSerializer


class PaymentMethodListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        methods = PaymentMethod.objects.filter(user=request.user)
        return success_response(data=PaymentMethodSerializer(methods, many=True).data)

    def post(self, request):
        serializer = PaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        is_first = not PaymentMethod.objects.filter(user=request.user).exists()

        pm = PaymentMethod.objects.create(
            user=request.user,
            type=d['type'],
            card_number=d['card_number'],
            holder_name=d['holder_name'],
            expiry=d['expiry'],
            is_default=is_first,
        )

        return success_response(data=PaymentMethodSerializer(pm).data, status_code=201)


class PaymentMethodSetDefaultView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            pm = PaymentMethod.objects.get(id=pk, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Karta topilmadi'}
            }, status=404)

        PaymentMethod.objects.filter(user=request.user).update(is_default=False)
        pm.is_default = True
        pm.save()

        return success_response(data=PaymentMethodSerializer(pm).data)


class PaymentMethodDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            pm = PaymentMethod.objects.get(id=pk, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Karta topilmadi'}
            }, status=404)

        was_default = pm.is_default
        pm.delete()

        if was_default:
            first = PaymentMethod.objects.filter(user=request.user).first()
            if first:
                first.is_default = True
                first.save()

        return success_response(message="Karta o'chirildi")
