from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio
from channels.layers import get_channel_layer

from rides.models import Driver


class DriverCountConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "driver_count"

        # Join the room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        count = await self.get_driver_count()

        await self.accept()
        await self.send(text_data=json.dumps({"type": "driver_count_message", "count": count}))

    async def disconnect(self, close_code):
        # Leave the room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def driver_count_message(self, event):
        count = event["count"]

        # Send a message to WebSocket
        await self.send(text_data=json.dumps({"type": "driver_count_message", "count": count}))

    @classmethod
    async def update_driver_count(cls):
        channel_layer = get_channel_layer()

        driver_count = await cls.get_driver_count()

        await channel_layer.group_send("driver_count", {"type": "driver_count_message", "count": driver_count})

    @staticmethod
    @database_sync_to_async
    def get_driver_count():
        return Driver.objects.count()


async def update_driver_count_async():
    consumer = DriverCountConsumer()
    await consumer.update_driver_count()
