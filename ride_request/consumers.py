
from datetime import datetime
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from channels.generic.websocket import  AsyncWebsocketConsumer
from user_account.models import User
import json
from channels.layers import get_channel_layer
from .models import RideRequest



channel_layer = get_channel_layer()

class PassengerConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        # Extract the user ID from the WebSocket URL
        user_id = self.scope['url_route']['kwargs']['user_id']

        # Check if the user ID is valid (e.g. exists in the database)
        try:
            self.user = await sync_to_async(User.objects.get)(id=user_id)
        except User.DoesNotExist:
            await self.close()
            return
        
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'create_ride_request':
            result = await self.create_ride_request(data)
            await self.send(json.dumps(result))
            await self.send_pending_ride_requests_to_drivers()

    
    @database_sync_to_async
    def create_ride_request(self, data):
        try:
            pickup_time_str = data['pickup_time']
            dropoff_time_str = data['dropoff_time']
            pickup_time = datetime.strptime(pickup_time_str, '%Y-%m-%dT%H:%M:%S')
            dropoff_time = datetime.strptime(dropoff_time_str, '%Y-%m-%dT%H:%M:%S')
            ride_request = RideRequest(
                user=self.user,
                pickup_latitude=data['pickup_latitude'],
                pickup_longitude=data['pickup_longitude'],
                dropoff_latitude=data['dropoff_latitude'],
                dropoff_longitude=data['dropoff_longitude'],
                pickup_address=data['pickup_address'],
                dropoff_address=data['dropoff_address'],
                pickup_time=pickup_time,
                dropoff_time=dropoff_time,
                ## TODO: fares, payment method
                # You can set the other fields, such as driver and actual_fare, when the ride is accepted or completed.
            )

            ride_request.save()
            return {
                'success': True,
                'message': 'Ride request created successfully',
                'id': str(ride_request.id),
                'pickup_latitude': ride_request.pickup_latitude,
                'pickup_longitude': ride_request.pickup_longitude,
                'dropoff_latitude': ride_request.dropoff_latitude,
                'dropoff_longitude': ride_request.dropoff_longitude,
                'pickup_address': ride_request.pickup_address,
                'dropoff_address': ride_request.dropoff_address,
                'pickup_time': ride_request.pickup_time.isoformat(),
                'dropoff_time': ride_request.dropoff_time.isoformat(),
                'status': ride_request.status
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
        

    @sync_to_async
    def get_pending_ride_requests(self):
        return list(RideRequest.objects.filter(status='pending'))

    async def send_pending_ride_requests_to_drivers(self):
        ride_requests = await self.get_pending_ride_requests()

        for ride_request in ride_requests:
            data = {
                'id': str(ride_request.id),
                'pickup_latitude': ride_request.pickup_latitude,
                'pickup_longitude': ride_request.pickup_longitude,
                'dropoff_latitude': ride_request.dropoff_latitude,
                'dropoff_longitude': ride_request.dropoff_longitude,
                'pickup_address': ride_request.pickup_address,
                'dropoff_address': ride_request.dropoff_address,
                'pickup_time': ride_request.pickup_time.isoformat(),
                'dropoff_time': ride_request.dropoff_time.isoformat(),
                'status': ride_request.status
            }

            await self.channel_layer.group_send(
                "drivers",
                {
                    'type': 'send_pending_ride_request',
                    'data': data
                }
            )

class DriverConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Extract the user ID from the WebSocket URL
        user_id = self.scope['url_route']['kwargs']['user_id']

        # Check if the user ID is valid (e.g. exists in the database)
        try:
            self.user = await sync_to_async(User.objects.get)(id=user_id)
        except User.DoesNotExist:
            await self.close()
            return
        # Check if the user is a student
        if self.user.role != 'student':
            await self.close()
            return
        
        await self.channel_layer.group_add(
            "drivers",
            self.channel_name
        )

        await self.accept()

    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'create_ride_request':
            result = await self.create_ride_request(data)
            await self.send(json.dumps(result))
    

    async def send_pending_ride_request(self, event):
        await self.send(json.dumps({
            'action': 'send_pending_ride_request',
            **event,
        }))