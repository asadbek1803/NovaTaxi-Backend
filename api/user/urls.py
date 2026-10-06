from django.urls import path

from . import views
from . import cars_views
from . import locations_views
from . import rides_views
from . import chat_views
from . import payments_views
from . import notifications_views
from . import support_views

urlpatterns = [
    # Auth
    path('auth/send-otp', views.SendOTPView.as_view(), name='send-otp'),
    path('auth/verify-otp', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/refresh-token', views.RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/logout', views.LogoutView.as_view(), name='logout'),

    # User Profile & Settings
    path('user/profile', views.ProfileView.as_view(), name='profile'),
    path('user/settings', views.UserSettingsView.as_view(), name='settings'),

    # Car Categories
    path('car-categories', cars_views.CarCategoryListView.as_view(), name='car-categories'),

    # Locations
    path('locations/search', locations_views.LocationSearchView.as_view(), name='location-search'),
    path('locations/popular', locations_views.PopularLocationsView.as_view(), name='popular-locations'),
    path('saved-locations', locations_views.SavedLocationListCreateView.as_view(), name='saved-locations'),
    path('saved-locations/<str:pk>', locations_views.SavedLocationDeleteView.as_view(), name='saved-location-delete'),

    # Rides
    path('rides/estimate', rides_views.RideEstimateView.as_view(), name='ride-estimate'),
    path('rides/request', rides_views.RideRequestView.as_view(), name='ride-request'),
    path('rides/history', rides_views.RideHistoryView.as_view(), name='ride-history'),
    path('rides/<str:pk>', rides_views.RideDetailView.as_view(), name='ride-detail'),
    path('rides/<str:pk>/driver-location', rides_views.RideDriverLocationView.as_view(), name='ride-driver-location'),
    path('rides/<str:pk>/cancel', rides_views.RideCancelView.as_view(), name='ride-cancel'),
    path('rides/<str:pk>/rate', rides_views.RideRateView.as_view(), name='ride-rate'),

    # Nearby Drivers
    path('drivers/nearby', rides_views.NearbyDriversView.as_view(), name='drivers-nearby'),

    # Chat
    path('messages/threads', chat_views.ThreadListView.as_view(), name='thread-list'),
    path('messages/threads/<str:pk>', chat_views.ThreadMessagesView.as_view(), name='thread-messages'),
    path('messages/threads/<str:pk>/send', chat_views.SendMessageView.as_view(), name='send-message'),
    path('messages/threads/<str:pk>/read', chat_views.MarkReadView.as_view(), name='mark-read'),

    # Payment Methods
    path('payment-methods', payments_views.PaymentMethodListCreateView.as_view(), name='payment-methods'),
    path('payment-methods/<str:pk>/default', payments_views.PaymentMethodSetDefaultView.as_view(), name='payment-method-default'),
    path('payment-methods/<str:pk>', payments_views.PaymentMethodDeleteView.as_view(), name='payment-method-delete'),

    # Notifications
    path('notifications/register', notifications_views.RegisterFCMTokenView.as_view(), name='register-fcm'),

    # Support
    path('support/ticket', support_views.SupportTicketView.as_view(), name='support-ticket'),
]
