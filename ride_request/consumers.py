from datetime import datetime
import traceback
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.messages import success
from user_account.models import User
import json
from channels.layers import get_channel_layer
from .models import RideRequest, Passenger
from django.core.cache import cache
from .mixins import RideRequestMixin
from collections import OrderedDict
from rides.models import Driver, DriverLocation


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

        passenger = await sync_to_async(Passenger.objects.get)(user_id=self.user_id)

        if (
            passenger.passenger_status == Passenger.STATUS_ACCEPTED
            or passenger.passenger_status == Passenger.STATUS_IN_PROGRESS
        ):
            cache_key = f"chatgroup_{self.user_id}"
            print(cache_key)
            group_name = cache.get(cache_key)
            print(group_name)
            await self.channel_layer.group_add(group_name, self.channel_name)

        cache.set(f"passengerconsumer_{self.user_id}", self.channel_name, 86400)  # 86400 seconds = 1 day

        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "create_ride_request":
            result = await self.create_ride_request(data)
            await self.send(json.dumps(result))
            if result["success"] == True:
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
                "type": "passenger_created_ride_request",
                "data": {
                    "id": str(ride_request.id),
                    "pickup_latitude": ride_request.pickup_latitude,
                    "pickup_longitude": ride_request.pickup_longitude,
                    "route_polygon": ride_request.route_polygon,
                    "dropoff_latitude": ride_request.dropoff_latitude,
                    "dropoff_longitude": ride_request.dropoff_longitude,
                    "pickup_address": ride_request.pickup_address,
                    "dropoff_address": ride_request.dropoff_address,
                    "status": ride_request.status,
                },
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

    async def driver_start_trip(self, event):
        response = {
            "success": True,
            "type": event["type"],
            "message": event["data"]["message"],
            "data": {
                "id": event["data"]["data"]["id"],
                "status": event["data"]["data"]["status"],
            },
        }
        await self.send(json.dumps(response))


class DriverConsumer(RideRequestMixin, AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = None

    async def connect(self):
        # Extract the user ID from the WebSocket URL
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]

        # Check if the user ID is valid (e.g. exists in the database)
        try:
            self.user = await sync_to_async(User.objects.get)(id=self.user_id)
        except User.DoesNotExist:
            await self.close()
            return
        # Check if the user is a student
        if self.user.role != "student":
            await self.close()
            return

        driver = await sync_to_async(Driver.objects.get)(user=self.user)
        driver_status = driver.jobDriverStatus
        response = None

        if driver_status == "enroute_pickup" or driver_status == "in_transit":
            ride_request_id = driver.ride_request
            cache_key = f"chatgroup_{ride_request_id}"

            self.group_name = cache.get(cache_key)
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        else:
            ride_requests = await self.get_pending_ride_requests()
            data_list = []
            for ride_request in ride_requests:
                data = {
                    "id": str(ride_request.id),
                    "pickup_latitude": ride_request.pickup_latitude,
                    "pickup_longitude": ride_request.pickup_longitude,
                    "dropoff_latitude": ride_request.dropoff_latitude,
                    "dropoff_longitude": ride_request.dropoff_longitude,
                    "pickup_address": ride_request.pickup_address,
                    "dropoff_address": ride_request.dropoff_address,
                    "status": ride_request.status,
                }
                data_list.append(data)
            response = {
                "action": "sending_pending_ride_request",
                "type": "send_pending_ride_request",
                "data": data_list,
            }
            await self.channel_layer.group_add("drivers", self.channel_name)

        await self.accept()

        if response is not None:
            await self.send(json.dumps(response))

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
        elif action == "start_trip":
            result = await self.start_trip(data)
            await self.send(json.dumps(result))
        elif action == "complete_trip":
            await self.complete_trip(data)

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

            passenger = await database_sync_to_async(Passenger.objects.get)(user_id=ride_request.user_id)
            passenger.passenger_status = Passenger.STATUS_ACCEPTED
            await database_sync_to_async(passenger.save)()

            await self.channel_layer.group_discard("drivers", self.channel_name)
            # Add both consumers to the group
            self.group_name = f"{ride_request.id}{driver.user_id}"
            cache.set(f"chatgroup_{ride_request.user_id}", self.group_name, None)
            print(f"chatgroup_{ride_request.user_id}")

            response_data_to_passenger = {
                "success": True,
                "message": "Ride request accepted successfully",
                "type": "driver_passenger_ride_request_accepted",
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
            if passenger_channel_name:
                await self.add_consumers_to_group(
                    self.group_name, self.channel_name, passenger_channel_name, response_data_to_passenger
                )

            response_data = {
                "success": True,
                "type": "driver_accepts_ride_request",
                "message": "Ride request accepted successfully",
                "data": {
                    "id": str(ride_request.id),
                    "status": ride_request.status,
                },
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

    async def driver_start_trip(self, event):
        response = {
            "success": True,
            "type": event["type"],
            "message": event["data"]["message"],
            "data": {
                "id": event["data"]["data"]["id"],
                "status": event["data"]["data"]["status"],
            },
        }
        await self.send(json.dumps(response))

    async def start_trip(self, data):
        try:
            ride_request_id = data["ride_request_id"]
            ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)

            if ride_request.status != RideRequest.STATUS_ACCEPTED:
                return {"success": False, "message": "Ride request is not accepted"}

            ride_request.status = RideRequest.STATUS_IN_PROGRESS
            ride_request.pickup_time = datetime.now()
            await database_sync_to_async(ride_request.save)()

            driver = await database_sync_to_async(lambda: self.user.driver)()
            driver.jobDriverStatus = Driver.STATUS_IN_TRANSIT
            await database_sync_to_async(driver.save)()

            response_data = {
                "success": True,
                "type": "driver_start_trip",
                "message": "Ride request starts successfully",
                "data": {
                    "id": str(ride_request.id),
                    "status": ride_request.status,
                },
            }

            cache_key = f"chatgroup_{ride_request.user_id}"

            self.group_name = cache.get(cache_key)
            print(self.group_name)
            await self.channel_layer.group_send(self.group_name, {"type": "driver_start_trip", "data": response_data})

            return response_data

        except RideRequest.DoesNotExist:
            return {"success": False, "message": "Ride request does not exist"}
        except Exception as e:
            tb = traceback.format_exc()
            return {"success": False, "message": str(e), "traceback": tb}

    async def remove_consumers_to_group(self, group_name, channel_name, passenger_channel_name, response):
        ride_request_id = response["ride_request_id"]
        ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
        data = {
            "success": True,
            "message": "Ride Request is completed successfully",
            "type": "driver_passenger_completed_ride_request",
            "data": {"id": str(ride_request.id)},
        }
        await self.channel_layer.group_send(group_name, {"type": "driver_accepts_ride_request", "data": data})
        await self.channel_layer.group_discard(group_name, channel_name)
        await self.channel_layer.group_discard(group_name, passenger_channel_name)
        await self.channel_layer.group_add("drivers", self.channel_name)

        cache.delete(f"chatgroup_{ride_request.user_id}")

    async def complete_trip(self, data):
        ride_request_id = data["ride_request_id"]
        ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
        ride_request.status = RideRequest.STATUS_COMPLETED
        ride_request.dropoff_time = datetime.now()
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
        data["type"] = "passenger_created_ride_request"
        for key, value in original_data.items():
            if key not in ["success", "message"]:
                data[key] = value

        await self.send(json.dumps(data))


class LocationConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def update_driver_location(self, user_id, latitude, longitude, polygon):
        try:
            driver_location = DriverLocation.objects.get(user_id=user_id)
            driver_location.latitude = latitude
            driver_location.longitude = longitude
            driver_location.polygon = polygon
            driver_location.save()
            return driver_location
        except DriverLocation.DoesNotExist:
            # Handle the case when the DriverLocation instance is not found.
            return None

    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        await self.channel_layer.group_add(self.user_id, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.user_id, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        type = data.get("type", "")
        if type == "location_update":
            driver_id = data.get("driver_id", "")
            latitude = data.get("latitude", 0)
            longitude = data.get("longitude", 0)
            polygon = data.get("polygon", "")

            # Save driver location in the database
            driver_location = await self.update_driver_location(driver_id, latitude, longitude, polygon)

            # Send location data to the passenger
            await self.channel_layer.group_send(
                self.user_id,
                {
                    "type": "location_update",
                    "driver_id": driver_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "polygon": polygon,
                },
            )

    async def location_update(self, event):
        response = {
            "success": True,
            "type": event["type"],
            "data": {
                "driver_id": event["driver_id"],
                "latitude": event["latitude"],
                "longitude": event["longitude"],
                "polygon": event["polygon"],
            },
        }
        await self.send(json.dumps(response))
