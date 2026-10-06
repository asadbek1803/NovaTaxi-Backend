import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger('api.driver.ws')


@database_sync_to_async
def get_user_from_token(token_str):
    from api.user.models import User
    try:
        access = AccessToken(token_str)
        user_id = access.get('user_id')
        if not user_id:
            return None
        return User.objects.filter(id=user_id, is_active=True).first()
    except Exception as exc:
        logger.warning('WS token invalid: %s', exc)
        return None


@database_sync_to_async
def get_driver_for_user(user, driver_id=None):
    from shared.models import Driver
    if not user or isinstance(user, AnonymousUser):
        return None
    qs = Driver.objects.filter(user=user)
    if driver_id:
        qs = qs.filter(id=driver_id)
    return qs.first()


@database_sync_to_async
def save_driver_location(driver_id, lat, lng):
    from shared.models import Driver, Ride
    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return None, None

    driver.current_lat = float(lat)
    driver.current_lng = float(lng)
    driver.save(update_fields=['current_lat', 'current_lng'])

    active_ride = Ride.objects.filter(
        driver=driver,
        status__in=['accepted', 'arriving', 'in_progress'],
    ).first()
    return driver, active_ride


@database_sync_to_async
def do_accept_order(driver_id, order_id):
    from shared.models import Driver
    from api.driver.views import accept_ride_for_driver
    from rest_framework.response import Response

    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return {'ok': False, 'message': 'Haydovchi topilmadi'}

    result = accept_ride_for_driver(driver, order_id)
    if isinstance(result, Response):
        data = result.data if hasattr(result, 'data') else {}
        msg = ''
        if isinstance(data, dict):
            err = data.get('error') or {}
            if isinstance(err, dict):
                msg = err.get('message', '')
            else:
                msg = data.get('message', str(err))
        return {'ok': False, 'message': msg or 'Buyurtmani qabul qilib bo\'lmadi'}
    return {'ok': True, 'ride_id': result.id, 'status': 'accepted'}


@database_sync_to_async
def do_decline_order(driver_id, order_id):
    from shared.models import Driver
    from api.driver.views import decline_ride_for_driver

    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return {'ok': False}
    ok = decline_ride_for_driver(driver, order_id)
    return {'ok': ok}


@database_sync_to_async
def do_ride_status(driver_id, order_id, status_value):
    from shared.models import Driver
    from api.driver.views import update_ride_status_for_driver
    from rest_framework.response import Response

    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return {'ok': False, 'message': 'Haydovchi topilmadi'}

    result = update_ride_status_for_driver(driver, order_id, status_value)
    if isinstance(result, Response):
        data = result.data if hasattr(result, 'data') else {}
        msg = ''
        if isinstance(data, dict):
            err = data.get('error') or {}
            if isinstance(err, dict):
                msg = err.get('message', '')
            else:
                msg = data.get('message', str(err))
        return {'ok': False, 'message': msg or 'Holat yangilanmadi'}
    return {
        'ok': True,
        'ride_id': result.id,
        'status': status_value,
    }


@database_sync_to_async
def set_driver_online(driver_id, online=True):
    from shared.models import Driver
    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return
    # WS ulanishi onlayn degani emas — faqat verified bo'lsa available saqlanadi
    if online and driver.is_verified and driver.is_active:
        # is_available ni majburan o'zgartirmaymiz; haydovchi toggle qiladi
        pass
    if not online:
        # Ulanish uzilganda joylashuvni saqlab qolamiz, available o'zgarmaydi
        pass


class DriverConsumer(AsyncWebsocketConsumer):
    """
    wss://.../ws/driver/?token=<access_token>&driver_id=<driver_id>

    Server → Client:
      - new_order
      - pong
      - driver_location_ack
      - order_accepted / order_error / ride_status_ack

    Client → Server:
      - driver_location {lat, lng}
      - ping
      - accept_order {order_id}
      - decline_order {order_id}
      - ride_status {order_id, status}
    """

    async def connect(self):
        query = self.scope.get('query_string', b'').decode()
        params = dict(
            part.split('=', 1) for part in query.split('&') if '=' in part
        )
        token = params.get('token', '')
        driver_id = params.get('driver_id', '')

        user = await get_user_from_token(token) if token else None
        if not user or not user.is_driver:
            await self.close(code=4001)
            return

        driver = await get_driver_for_user(user, driver_id or None)
        if not driver:
            await self.close(code=4003)
            return

        # driver_id berilgan bo'lsa, mos kelishi shart
        if driver_id and str(driver.id) != str(driver_id):
            await self.close(code=4003)
            return

        self.user = user
        self.driver = driver
        self.driver_id = driver.id
        self.group_name = f'driver_{self.driver_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add('drivers_online', self.channel_name)
        await self.accept()
        await set_driver_online(self.driver_id, True)

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'driver_id': self.driver_id,
            'message': 'WebSocket ulandi',
        }))
        logger.info('Driver WS connected: %s', self.driver_id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_discard('drivers_online', self.channel_name)
        if hasattr(self, 'driver_id'):
            await set_driver_online(self.driver_id, False)
            logger.info('Driver WS disconnected: %s code=%s', self.driver_id, close_code)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': "Noto'g'ri JSON",
            }))
            return

        msg_type = data.get('type', '')

        if msg_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

        elif msg_type == 'driver_location':
            await self._handle_location(data)

        elif msg_type == 'accept_order':
            await self._handle_accept(data)

        elif msg_type == 'decline_order':
            await self._handle_decline(data)

        elif msg_type == 'ride_status':
            await self._handle_ride_status(data)

        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Noma'lum xabar turi: {msg_type}",
            }))

    async def _handle_location(self, data):
        lat = data.get('lat')
        lng = data.get('lng')
        if lat is None or lng is None:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'lat va lng majburiy',
            }))
            return

        driver, active_ride = await save_driver_location(self.driver_id, lat, lng)

        # Hujjat: driver_location_ack
        await self.send(text_data=json.dumps({
            'type': 'driver_location_ack',
            'lat': float(lat),
            'lng': float(lng),
        }))

        # Admin panel
        if driver:
            await self.channel_layer.group_send(
                'admin_drivers',
                {
                    'type': 'driver_location_update',
                    'data': {
                        'id': driver.id,
                        'name': driver.name,
                        'phone': driver.phone,
                        'current_lat': float(lat),
                        'current_lng': float(lng),
                        'heading': driver.heading,
                        'is_available': driver.is_available,
                        'car_model': driver.car_model,
                        'license_plate': driver.license_plate,
                        'rating': driver.rating,
                    },
                },
            )

        # Faol safar bo'lsa yo'lovchiga
        if active_ride:
            await self.channel_layer.group_send(
                f'ride_{active_ride.id}_location',
                {
                    'type': 'driver_location',
                    'data': {
                        'type': 'driver_location',
                        'lat': float(lat),
                        'lng': float(lng),
                        'ride_id': active_ride.id,
                    },
                },
            )

    async def _handle_accept(self, data):
        order_id = data.get('order_id') or data.get('ride_id')
        if not order_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'order_id majburiy',
            }))
            return

        result = await do_accept_order(self.driver_id, order_id)
        if result.get('ok'):
            await self.send(text_data=json.dumps({
                'type': 'order_accepted',
                'order_id': order_id,
                'status': 'accepted',
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'order_error',
                'order_id': order_id,
                'message': result.get('message', 'Qabul qilinmadi'),
            }))

    async def _handle_decline(self, data):
        order_id = data.get('order_id') or data.get('ride_id')
        if not order_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'order_id majburiy',
            }))
            return

        await do_decline_order(self.driver_id, order_id)
        await self.send(text_data=json.dumps({
            'type': 'order_declined',
            'order_id': order_id,
        }))

    async def _handle_ride_status(self, data):
        order_id = data.get('order_id') or data.get('ride_id')
        status_value = data.get('status', '')
        if not order_id or not status_value:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'order_id va status majburiy',
            }))
            return

        result = await do_ride_status(self.driver_id, order_id, status_value)
        if result.get('ok'):
            await self.send(text_data=json.dumps({
                'type': 'ride_status_ack',
                'order_id': order_id,
                'status': status_value,
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'order_id': order_id,
                'message': result.get('message', 'Holat yangilanmadi'),
            }))

    # ── Channel layer event handlers ──

    async def new_order(self, event):
        """Server yangi buyurtmani haydovchiga yuboradi."""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order': event.get('order', {}),
        }))

    async def order_cancelled(self, event):
        await self.send(text_data=json.dumps({
            'type': 'order_cancelled',
            'order_id': event.get('order_id'),
            'message': event.get('message', 'Buyurtma bekor qilindi'),
        }))

    async def driver_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event.get('title', ''),
            'body': event.get('body', ''),
            'data': event.get('data', {}),
        }))


from django.urls import path

websocket_urlpatterns = [
    path('ws/driver/', DriverConsumer.as_asgi()),
    path('ws/driver', DriverConsumer.as_asgi()),
]
