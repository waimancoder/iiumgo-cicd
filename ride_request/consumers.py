from datetime import datetime
import traceback
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import ride_request
from user_account.models import User
import json
from channels.layers import get_channel_layer
from .models import RideRequest
from django.core.cache import cache
import asyncio
from .mixins import RideRequestMixin
from collections import OrderedDict
from rides.models import Driver


channel_layer = get_channel_layer()


class PassengerConsumer(RideRequestMixin, AsyncWebsocketConsumer):
    async def connect(self):
        # Extract the user ID from the WebSocket URL
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]

        # Check if the user ID is valid (e.g. exists in the database)
        try:
            self.user = await sync_to_async(User.objects.get)(id=self.user_id)
        except User.DoesNotExist:
            await self.close()
            return

        cache.set(f"passengerconsumer_{self.user_id}", self.channel_name, 86400)  # 86400 seconds = 1 day

        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "create_ride_request":
            result = await self.create_ride_request(data)
            await self.send(json.dumps(result))
            if result["status"] == "success":
                await self.send_new_ride_request_to_drivers(result)
        elif action == "send_chat_message":
            await self.send_chat_message(data)

    async def send_chat_message(self, data):
        message = data["message"]
        user_id = self.user_id
        group_name = cache.get(f"chatgroup_{self.user_id}")
        await self.channel_layer.group_send(
            group_name,
            {
                "type": "chat_message",
                "user_id": user_id,
                "message": message,
            },
        )

    async def chat_message(self, event):
        message = event["message"]
        user_id = event["user_id"]
        await self.send(json.dumps({"action": "chat_message", "user_id": user_id, "message": message}))

    @database_sync_to_async
    def create_ride_request(self, data):
        try:
            ride_request = RideRequest(
                user=self.user,
                pickup_latitude=data["pickup_latitude"],
                pickup_longitude=data["pickup_longitude"],
                dropoff_latitude=data["dropoff_latitude"],
                dropoff_longitude=data["dropoff_longitude"],
                pickup_address=data["pickup_address"],
                dropoff_address=data["dropoff_address"],
                route_polygon=data["route_polygon"],
                ## TODO: fares, payment method
                # You can set the other fields, such as driver and actual_fare, when the ride is accepted or completed.
            )

            ride_request.save()
            response_data = {
                "success": True,
                "message": "Ride request created successfully",
                "id": str(ride_request.id),
                "pickup_latitude": ride_request.pickup_latitude,
                "pickup_longitude": ride_request.pickup_longitude,
                "route_polygon": ride_request.route_polygon,
                "dropoff_latitude": ride_request.dropoff_latitude,
                "dropoff_longitude": ride_request.dropoff_longitude,
                "pickup_address": ride_request.pickup_address,
                "dropoff_address": ride_request.dropoff_address,
                "status": ride_request.status,
            }

            return response_data
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def send_new_ride_request_to_drivers(self, data):
        await self.channel_layer.group_send("drivers", {"type": "send_new_ride_request", "data": data})

    async def send_new_ride_request(self, event):
        data = event["data"]
        await self.send(json.dumps(data))

    async def driver_accepts_ride_request(self, event):
        await self.send(json.dumps(event["data"]))


class DriverConsumer(RideRequestMixin, AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = None

    async def connect(self):
        # Extract the user ID from the WebSocket URL
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        print(f"User ID: {self.user_id}")

        # Check if the user ID is valid (e.g. exists in the database)
        try:
            self.user = await sync_to_async(User.objects.get)(id=self.user_id)
            print(self.user_id)
        except User.DoesNotExist:
            print("user does not exist")
            await self.close()
            return
        # Check if the user is a student
        if self.user.role != "student":
            print("user is not a student")
            await self.close()
            return

        print("user is a student")
        driver = await sync_to_async(Driver.objects.get)(user=self.user)
        driver_status = driver.jobDriverStatus

        if driver_status == Driver.STATUS_ENROUTE_PICKUP and driver_status == Driver.STATUS_IN_TRANSIT:
            ride_request_id = driver.ride_request.id
            cache_key = f"chatgroup_{ride_request_id}"
            group_name = cache.get(cache_key)
            await self.channel_layer.group_add(group_name, self.channel_name)
        else:
            await self.channel_layer.group_add("drivers", self.channel_name)
            await self.send_pending_ride_requests_to_drivers()
            print("connected")

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("drivers", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "create_ride_request":
            result = await self.create_ride_request(data)
            await self.send(json.dumps(result))
        elif action == "accept_ride_request":
            result = await self.accept_ride_request(data)
            await self.send(json.dumps(result))
        elif action == "send_chat_message":
            await self.send_chat_message(data)

    async def send_pending_ride_request(self, event):
        await self.send(
            json.dumps(
                {
                    "action": "sending_pending_ride_request",
                    **event,
                }
            )
        )

    async def send_chat_message(self, event):
        message = event["message"]
        user_id = self.user_id
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "user_id": user_id,
                "message": message,
            },
        )

    async def chat_message(self, event):
        message = event["message"]
        user_id = event["user_id"]
        await self.send(json.dumps({"action": "chat_message", "user_id": user_id, "message": message}))

    async def add_consumers_to_group(self, group_name, channel_name, passenger_channel_name, data):
        print("adding consumer")
        print(channel_name)
        await self.channel_layer.group_add(group_name, channel_name)
        await self.channel_layer.group_add(group_name, passenger_channel_name)
        await self.channel_layer.group_send(group_name, {"type": "driver_accepts_ride_request", "data": data})

    async def accept_ride_request(self, data):
        try:
            ride_request_id = data["ride_request_id"]
            ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)

            if ride_request.status != RideRequest.STATUS_PENDING:
                return {"success": False, "message": "Ride request is not pending"}

            driver = await database_sync_to_async(lambda: self.user.driver)()
            ride_request.status = RideRequest.STATUS_ACCEPTED
            ride_request.driver = driver
            driver.jobDriverStatus = Driver.STATUS_ENROUTE_PICKUP
            driver.ride_request = ride_request.user_id
            await database_sync_to_async(ride_request.save)()
            await database_sync_to_async(driver.save)()

            await self.channel_layer.group_discard("drivers", self.channel_name)
            # Add both consumers to the group
            self.group_name = f"{ride_request.id}{driver.user_id}"
            cache.set(f"chatgroup_{ride_request.user_id}", self.group_name, None)

            response_data_to_passenger = {
                "success": True,
                "message": "Ride request accepted successfully",
                "action": "driver-passenger-accepts-ride-request",
                "data": {
                    "id": str(ride_request.id),
                    "status": ride_request.status,
                    "driver_id": str(driver.user_id),
                    "driver_name": driver.user.fullname,
                    "vehicle_registration_number": driver.vehicle_registration_number
                    if driver.vehicle_registration_number
                    else "",
                    "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                    "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                    "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                    "rating": "__average_rating_placeholder__",
                },
            }

            average_rating = await sync_to_async(getattr)(driver, "average_rating")
            response_data_to_passenger["data"]["rating"] = average_rating if average_rating else ""

            passenger_channel_name = cache.get(f"passengerconsumer_{ride_request.user_id}")
            print(passenger_channel_name)
            if passenger_channel_name:
                await self.add_consumers_to_group(
                    self.group_name, self.channel_name, passenger_channel_name, response_data_to_passenger
                )

            response_data = {
                "success": True,
                "message": "Ride request accepted successfully",
                "id": str(ride_request.id),
                "status": ride_request.status,
            }
            await self.channel_layer.group_send(
                "drivers", {"type": "driver_accepts_ride_request", "data": response_data}
            )

            return response_data
        except RideRequest.DoesNotExist:
            return {"success": False, "message": "Ride request does not exist"}
        except Exception as e:
            tb = traceback.format_exc()
            return {"success": False, "message": str(e), "traceback": tb}

    async def start_trip(self, data):
        ride_request_id = data["ride_request_id"]
        ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
        ride_request.status = RideRequest.STATUS_IN_PROGRESS
        await database_sync_to_async(ride_request.save)()

        driver = await database_sync_to_async(lambda: self.user.driver)()
        driver.jobDriverStatus = Driver.STATUS_IN_TRANSIT
        await database_sync_to_async(driver.save)()

    async def remove_consumers_to_group(self, group_name, channel_name, passenger_channel_name, response):
        print("removing consumer")
        print(channel_name)
        ride_request_id = response["ride_request_id"]
        ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
        data = {
            "message": "Ride Request is completed successfully",
            "action": "driver-passenger-completes-ride-request",
            "id": str(ride_request.id),
        }
        await self.channel_layer.group_send(group_name, {"type": "driver_accepts_ride_request", "data": data})
        await self.channel_layer.group_discard(group_name, channel_name)
        await self.channel_layer.group_discard(group_name, passenger_channel_name)

        cache.delete(f"chatgroup_{ride_request.user_id}")

    async def complete_trip(self, data):
        ride_request_id = data["ride_request_id"]
        ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
        ride_request.status = RideRequest.STATUS_COMPLETED
        await database_sync_to_async(ride_request.save)()

        driver = await database_sync_to_async(lambda: self.user.driver)()
        driver.jobDriverStatus = Driver.STATUS_AVAILABLE
        await database_sync_to_async(driver.save)()

        passenger_channel_name = cache.get(f"passengerconsumer_{ride_request.user_id}")
        if passenger_channel_name:
            await self.remove_consumers_to_group(self.group_name, self.channel_name, passenger_channel_name, data)

    async def driver_accepts_ride_request(self, event):
        await self.send(json.dumps(event["data"]))

    async def send_new_ride_request(self, event):
        original_data = event["data"]

        # Create a new ordered dictionary and add the keys in the desired order
        data = OrderedDict()
        data["success"] = original_data["success"]
        data["action"] = "passenger_created_ride_request"
        for key, value in original_data.items():
            if key not in ["success", "message"]:
                data[key] = value

        await self.send(json.dumps(data))
