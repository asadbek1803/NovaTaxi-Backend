from django.urls import path, include

urlpatterns = [
    # User (yo'lovchi) API
    path('v1/user/', include('api.user.urls')),

    # Driver API — ichki yo'llar (/api/v1/driver/...)
    path('v1/driver/', include('api.driver.urls')),

    # Hujjatga mos haydovchi endpointlari:
    #   POST /api/v1/auth/send-otp
    #   POST /api/v1/auth/verify-otp
    #   POST /api/v1/auth/register
    #   GET  /api/v1/drivers/status
    #   POST /api/v1/drivers/onboarding
    #   POST /api/v1/drivers/fcm-token
    path('v1/auth/', include('api.driver.auth_urls')),
    path('v1/drivers/', include('api.driver.driver_urls')),

    # Admin API
    path('v1/admin/', include('api.admin.urls')),
]
