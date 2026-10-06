from django.urls import path

from . import views

app_name = 'panel'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('map/', views.map_view, name='map'),
    path('drivers/', views.drivers_list_view, name='drivers'),
    path('users/', views.users_list_view, name='users'),
    path('tariffs/', views.tariffs_view, name='tariffs'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('support/', views.support_view, name='support'),
    path('kyc/', views.kyc_list_view, name='kyc'),
    path('kyc/<str:driver_id>/approve/', views.kyc_approve_view, name='kyc-approve'),
    path('kyc/<str:driver_id>/reject/', views.kyc_reject_view, name='kyc-reject'),
    path('finances/', views.finances_view, name='finances'),
    path('dispatch/', views.dispatch_view, name='dispatch'),
    path('promocodes/', views.promocodes_view, name='promocodes'),
    path('reviews/', views.reviews_view, name='reviews'),
    path('settings/', views.settings_view, name='settings'),
    path('regions/', views.regions_view, name='regions'),
    path('regions/create/', views.region_create, name='region-create'),
    path('regions/<str:region_id>/update/', views.region_update, name='region-update'),
    path('regions/<str:region_id>/delete/', views.region_delete, name='region-delete'),
    path('districts/', views.districts_view, name='districts'),
    path('districts/create/', views.district_create, name='district-create'),
    path('districts/<str:district_id>/update/', views.district_update, name='district-update'),
    path('districts/<str:district_id>/delete/', views.district_delete, name='district-delete'),
    path('mfy/', views.mfy_view, name='mfy'),
    path('mfy/create/', views.mfy_create, name='mfy-create'),
    path('mfy/<str:mfy_id>/update/', views.mfy_update, name='mfy-update'),
    path('mfy/<str:mfy_id>/delete/', views.mfy_delete, name='mfy-delete'),
    path('streets/create/', views.street_create, name='street-create'),
    path('streets/<str:street_id>/delete/', views.street_delete, name='street-delete'),
    path('api/regions/', views.api_regions, name='api-regions'),
    path('api/drivers/locations/', views.api_drivers_locations, name='api-drivers-locations'),
    path('api/active-rides/', views.api_active_rides, name='api-active-rides'),
]
