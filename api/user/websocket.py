import json

from channels.generic.websocket import AsyncWebsocketConsumer


class RideLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group = f'ride_{self.ride_id}_location'
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        pass

    async def driver_location(self, event):
        await self.send(text_data=json.dumps(event['data']))


class RideStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group = f'ride_{self.ride_id}_status'
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        pass

    async def ride_status(self, event):
        await self.send(text_data=json.dumps(event['data']))


class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group = 'messages_global'
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        pass

    async def new_message(self, event):
        await self.send(text_data=json.dumps(event['data']))
