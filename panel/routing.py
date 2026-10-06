from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/panel/drivers/', consumers.AdminDriverLocationConsumer.as_asgi()),
]
