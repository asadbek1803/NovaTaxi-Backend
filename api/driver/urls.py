from django.urls import path

from . import views

urlpatterns = [
    # ── Auth (ichki /v1/driver/auth/...) ──
    path('auth/send-otp', views.SendOTPView.as_view(), name='driver-send-otp'),
    path('auth/verify-otp', views.VerifyOTPView.as_view(), name='driver-verify-otp'),
    path('auth/register', views.RegisterDriverView.as_view(), name='driver-register'),
    path('auth/refresh-token', views.RefreshTokenView.as_view(), name='driver-refresh-token'),
    path('auth/logout', views.LogoutView.as_view(), name='driver-logout'),

    # ── Profile & Onboarding ──
    path('profile/onboarding', views.DriverOnboardingView.as_view(), name='driver-onboarding'),
    path('profile/status', views.DriverStatusView.as_view(), name='driver-status'),
    path('profile/availability', views.ToggleAvailabilityView.as_view(), name='driver-availability'),
    path('profile/earnings', views.DriverEarningsView.as_view(), name='driver-earnings'),
    path('profile/fcm-token', views.DriverFCMTokenView.as_view(), name='driver-fcm-token-legacy'),

    # ── Rides ──
    path('rides/available', views.AvailableRidesView.as_view(), name='driver-available-rides'),
    path('rides/active', views.ActiveRideView.as_view(), name='driver-active-ride'),
    path('rides/history', views.RideHistoryView.as_view(), name='driver-ride-history'),
    path('rides/<str:ride_id>/accept', views.AcceptRideView.as_view(), name='driver-accept-ride'),
    path('rides/<str:ride_id>/status', views.RideStatusView.as_view(), name='driver-ride-status'),

    # ── Location ──
    path('location/update', views.LocationUpdateView.as_view(), name='driver-location-update'),
]
