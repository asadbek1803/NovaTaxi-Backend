"""Hujjat: /v1/auth/* — haydovchi autentifikatsiyasi."""
from django.urls import path

from . import views

urlpatterns = [
    path('send-otp', views.SendOTPView.as_view(), name='v1-auth-send-otp'),
    path('verify-otp', views.VerifyOTPView.as_view(), name='v1-auth-verify-otp'),
    path('register', views.RegisterDriverView.as_view(), name='v1-auth-register'),
    path('refresh-token', views.RefreshTokenView.as_view(), name='v1-auth-refresh-token'),
    path('logout', views.LogoutView.as_view(), name='v1-auth-logout'),
]
