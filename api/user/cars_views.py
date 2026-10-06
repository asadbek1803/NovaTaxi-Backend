from rest_framework import permissions
from rest_framework.views import APIView

from api.utils import success_response
from shared.models import CarCategory
from api.user.serializers import CarCategorySerializer


class CarCategoryListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        categories = CarCategory.objects.filter(is_active=True)
        return success_response(data=CarCategorySerializer(categories, many=True).data)
