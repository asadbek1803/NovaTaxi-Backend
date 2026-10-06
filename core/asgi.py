import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

from api.user.websocket_urls import websocket_urlpatterns as user_ws
from api.driver.websocket import websocket_urlpatterns as driver_ws
from panel.routing import websocket_urlpatterns as panel_ws

all_ws = user_ws + driver_ws + panel_ws

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(all_ws)
    ),
})
