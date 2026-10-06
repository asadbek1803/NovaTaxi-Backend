"""Hujjat: /v1/drivers/* — haydovchi profili."""
from django.urls import path

from . import views

urlpatterns = [
    path('status', views.DriverAppStatusView.as_view(), name='v1-drivers-status'),
    path('onboarding', views.DriverOnboardingDocView.as_view(), name='v1-drivers-onboarding'),
    path('fcm-token', views.DriverFCMTokenView.as_view(), name='v1-drivers-fcm-token'),
    # Qo'shimcha foydali endpointlar
    path('availability', views.ToggleAvailabilityView.as_view(), name='v1-drivers-availability'),
    path('earnings', views.DriverEarningsView.as_view(), name='v1-drivers-earnings'),
    path('rides/available', views.AvailableRidesView.as_view(), name='v1-drivers-available-rides'),
    path('rides/active', views.ActiveRideView.as_view(), name='v1-drivers-active-ride'),
    path('rides/history', views.RideHistoryView.as_view(), name='v1-drivers-ride-history'),
    path('rides/<str:ride_id>/accept', views.AcceptRideView.as_view(), name='v1-drivers-accept-ride'),
    path('rides/<str:ride_id>/status', views.RideStatusView.as_view(), name='v1-drivers-ride-status'),
    path('location', views.LocationUpdateView.as_view(), name='v1-drivers-location'),
]
