import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class AdminDriverLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group = 'admin_drivers'
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        drivers = await self.get_all_drivers()
        rides = await self.get_all_active_rides()
        await self.send(text_data=json.dumps({
            'type': 'map_initial',
            'drivers': drivers,
            'rides': rides,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        pass

    async def driver_location_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'driver_location_update',
            'driver': event['data'],
        }))

    async def driver_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'driver_status_update',
            'driver': event['data'],
        }))

    async def ride_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ride_update',
            'ride': event['data'],
        }))

    async def ride_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ride_delete',
            'ride_id': event['ride_id'],
        }))

    @database_sync_to_async
    def get_all_drivers(self):
        from shared.models import Driver, Ride
        drivers = list(
            Driver.objects.filter(is_active=True).values(
                'id', 'name', 'phone', 'current_lat', 'current_lng',
                'heading', 'is_available', 'car_model', 'license_plate',
                'rating', 'is_verified',
            )
        )
        driver_map = {d['id']: d for d in drivers}
        active_rides = Ride.objects.filter(
            status__in=['accepted', 'arriving', 'in_progress']
        ).select_related('passenger').only(
            'id', 'driver_id', 'passenger_id', 'from_lat', 'from_lng',
            'from_address', 'status', 'price', 'category_id'
        )
        for ride in active_rides:
            did = ride.driver_id
            if did in driver_map:
                if 'rides' not in driver_map[did]:
                    driver_map[did]['rides'] = []
                driver_map[did]['rides'].append({
                    'id': ride.id,
                    'passenger_name': ride.passenger.full_name or ride.passenger.phone,
                    'passenger_id': ride.passenger.id,
                    'from_address': ride.from_address,
                    'from_lat': ride.from_lat,
                    'from_lng': ride.from_lng,
                    'status': ride.status,
                    'price': ride.price,
                    'category': ride.category_id,
                })
        return drivers

    @database_sync_to_async
    def get_all_active_rides(self):
        from shared.models import Ride
        rides = Ride.objects.filter(
            status__in=['pending', 'accepted', 'arriving', 'in_progress']
        ).select_related('passenger', 'driver').order_by('-created_at')
        data = []
        for ride in rides:
            item = {
                'id': ride.id,
                'passenger': {
                    'id': ride.passenger.id,
                    'name': ride.passenger.full_name or ride.passenger.phone,
                    'phone': ride.passenger.phone,
                },
                'from_lat': ride.from_lat,
                'from_lng': ride.from_lng,
                'from_address': ride.from_address,
                'to_lat': ride.to_lat,
                'to_lng': ride.to_lng,
                'to_address': ride.to_address,
                'status': ride.status,
                'price': ride.price,
                'category': ride.category_id or '',
                'driver_id': ride.driver_id or '',
            }
            if ride.driver_id:
                item['driver'] = {
                    'id': ride.driver.id,
                    'name': ride.driver.name,
                    'phone': ride.driver.phone,
                    'car_model': ride.driver.car_model,
                    'license_plate': ride.driver.license_plate,
                }
            data.append(item)
        return data
