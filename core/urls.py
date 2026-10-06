from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Asosiy API (prefix: /api/)
    path('api/', include('api.urls')),
    # Hujjat Base URL mosligi: https://api.novataxi.uz/v1/...
    # (mobil ilova /v1/auth/... va /v1/drivers/... chaqiradi)
    path('v1/auth/', include('api.driver.auth_urls')),
    path('v1/drivers/', include('api.driver.driver_urls')),
    path('panel/', include('panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
