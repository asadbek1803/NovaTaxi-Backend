from django.urls import path

from . import websocket

websocket_urlpatterns = [
    path('ws/rides/<str:ride_id>/location', websocket.RideLocationConsumer.as_asgi()),
    path('ws/rides/<str:ride_id>/status', websocket.RideStatusConsumer.as_asgi()),
    path('ws/messages', websocket.MessageConsumer.as_asgi()),
]
