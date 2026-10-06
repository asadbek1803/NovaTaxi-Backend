from django.urls import path

from . import views

urlpatterns = [
    path('dashboard', views.AdminDashboardView.as_view(), name='admin-dashboard'),
]
