from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils import success_response
from shared.models import Location, SavedLocation
from api.user.serializers import (
    LocationSerializer,
    SavedLocationCreateSerializer,
    SavedLocationSerializer,
)


class LocationSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = request.query_params.get('q', '')
        locations = Location.objects.all()
        if q:
            locations = locations.filter(name__icontains=q) | locations.filter(address__icontains=q)
        return success_response(data=LocationSerializer(locations[:20], many=True).data)


class PopularLocationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        locations = Location.objects.all()[:10]
        return success_response(data=LocationSerializer(locations, many=True).data)


class SavedLocationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        saved = SavedLocation.objects.filter(user=request.user)
        return success_response(data=SavedLocationSerializer(saved, many=True).data)

    def post(self, request):
        serializer = SavedLocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = SavedLocation.objects.create(user=request.user, **serializer.validated_data)
        return success_response(
            data=SavedLocationSerializer(saved).data,
            status_code=201
        )


class SavedLocationDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            saved = SavedLocation.objects.get(id=pk, user=request.user)
        except SavedLocation.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Manzil topilmadi'}
            }, status=404)
        saved.delete()
        return success_response(message="Manzil o'chirildi")
