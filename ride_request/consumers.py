from datetime import date, datetime
import os
import traceback
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from payment.models import CommissionHistory, DriverEarning, DriverEwallet
from ride_request.pricing import get_commission_amount
from user_account.models import User
import json
from channels.layers import get_channel_layer
from .models import CancelRateDriver, Rating, RideRequest, Passenger
from django.core.cache import cache
from .mixins import RideRequestMixin
from collections import OrderedDict
from rides.models import Driver, DriverLocation
import redis
import logging

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

host = os.environ.get("redis_client_host")
password = os.environ.get("redis_client_password")
port = os.environ.get("redis_client_port")
redis_client = redis.Redis(host=host, port=port, password=password)

# a list of all the channels that are currently connected


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)


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
        archived_messages = []

        if (
            passenger.passenger_status == Passenger.STATUS_ACCEPTED
            or passenger.passenger_status == Passenger.STATUS_IN_PROGRESS
        ):
            cache_key = f"cg_{self.user_id}"
            group_name = cache.get(cache_key)

            event_key = f"cg_{self.user_id}"
            messages = redis_client.hgetall(event_key)
            for value in messages.values():
                decoded_value = json.loads(value.decode("utf-8"))
                archived_messages.append(decoded_value)

            sorted_messages = sorted(
                archived_messages, key=lambda msg: datetime.fromisoformat(msg["time"]), reverse=True
            )
            archived_messages = sorted_messages

            await self.channel_layer.group_add(group_name, self.channel_name)

        cache.set(f"passengerconsumer_{self.user_id}", self.channel_name, 86400)  # 86400 seconds = 1 day

        await self.accept()

        if archived_messages != []:
            await self.send(json.dumps({"type": "archived_messages", "data": archived_messages}))

        # TODO - Notify frontend passenger state
        if passenger.passenger_status == Passenger.STATUS_ACCEPTED:
            ride_request = await sync_to_async(
                RideRequest.objects.filter(status=RideRequest.STATUS_ACCEPTED)
                .filter(user_id=self.user_id)
                .order_by("-created_at")
                .first
            )()
            driver = await sync_to_async(Driver.objects.get)(id=ride_request.driver_id)
            driver_details = await sync_to_async(User.objects.get)(id=driver.user_id)

            await self.send(
                json.dumps(self.passenger_statusDetails(ride_request, driver, driver_details, status="accepted"))
            )
        elif passenger.passenger_status == Passenger.STATUS_IN_PROGRESS:
            ride_request = await sync_to_async(
                RideRequest.objects.filter(status=RideRequest.STATUS_IN_PROGRESS)
                .filter(user_id=self.user_id)
                .order_by("-created_at")
                .first
            )()
            driver = await sync_to_async(Driver.objects.get)(id=ride_request.driver_id)
            driver_details = await sync_to_async(User.objects.get)(id=driver.user_id)
            await self.send(
                json.dumps(
                    self.passenger_statusDetails(
                        ride_request,
                        driver,
                        driver_details,
                        status="in_progress",
                    )
                )
            )
        elif passenger.passenger_status == Passenger.STATUS_PENDING:
            ride_request = await sync_to_async(
                RideRequest.objects.filter(status=RideRequest.STATUS_PENDING)
                .filter(user_id=self.user_id)
                .order_by("-created_at")
                .first
            )()
            await self.send(
                json.dumps(
                    {
                        "type": "passenger_status",
                        "passenger_status": "pending",
                        "data": {
                            "ride_request_info": {
                                "id": str(ride_request.id),
                                "pickup_latitude": ride_request.pickup_latitude,
                                "pickup_longitude": ride_request.pickup_longitude,
                                "polyline": ride_request.route_polygon,
                                "pickup_address": ride_request.pickup_address,
                                "dropoff_address": ride_request.dropoff_address,
                                "dropoff_latitude": ride_request.dropoff_latitude,
                                "dropoff_longitude": ride_request.dropoff_longitude,
                                "vehicle_type": ride_request.vehicle_type,
                                "price": float(ride_request.price),
                                "distance": ride_request.distance,
                                "details": ride_request.special_requests,
                                "status": ride_request.status,
                                "created_at": ride_request.created_at.isoformat(),
                                "isFemaleDriver": ride_request.isFemaleDriver,
                            },
                            "passenger_info": {
                                "passenger_id": str(self.user.id),
                                "passenger_name": self.user.fullname,
                                "passenger_phone_number": self.user.phone_no,
                                "passenger_gender": self.user.gender,
                            },
                            "driver_info": {
                                "driver_id": "",
                                "driver_status": "",
                                "driver_name": "",
                                "driver_profile_pic": "",
                                "driver_phone_number": "",
                                "vehicle_registration_number": "",
                                "vehicle_manufacturer": "",
                                "vehicle_model": "",
                                "vehicle_color": "",
                                "vehicle_type": "",
                            },
                        },
                    }
                )
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "create_ride_request":
                result = await self.create_ride_request(data)
                await self.send(json.dumps(result))
                if result["success"] == True:
                    await self.send_new_ride_request_to_drivers(result)
            elif action == "send_chat_message":
                await self.send_chat_message(data)
            elif action == "cancel_ride_request":
                result = await self.cancel_ride_request(data)
                await self.send(json.dumps(result))
        except Exception as e:
            logger.error(e)
            await self.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": str(e),
                    }
                )
            )

    async def send_chat_message(self, data):
        message = data["message"]
        user_id = self.user_id
        group_name = cache.get(f"cg_{user_id}")
        event_key = f"cg_{user_id}"
        event_dict = {
            "type": "chat_message",
            "user_id": user_id,
            "message": message,
            "time": datetime.now().isoformat(),
        }
        redis_client.hset(name=event_key, key=datetime.now().timestamp(), value=json.dumps(event_dict))
        await self.channel_layer.group_send(
            group_name,
            {"type": "chat_message", "user_id": user_id, "message": message, "time": datetime.now().isoformat()},
        )

    async def chat_message(self, event):
        message = event["message"]
        user_id = event["user_id"]
        event_dict = {
            "type": "chat_message",
            "user_id": user_id,
            "message": message,
            "time": datetime.now().isoformat(),
        }
        try:
            if event["event"] == "automated_message":
                event_dict = {
                    "type": "automated_message",
                    "message": event["message"],
                    "user_id": event["user_id"],
                    "time": event["time"],
                }
        except:
            pass
        await self.send(json.dumps(event_dict))

    @database_sync_to_async
    def create_ride_request(self, data):
        try:
            passenger = Passenger.objects.get(user_id=self.user_id)
            if (
                passenger.passenger_status == Passenger.STATUS_ACCEPTED
                or passenger.passenger_status == Passenger.STATUS_IN_PROGRESS
            ):
                return {"success": False, "message": "You have an ongoing ride request"}
            else:
                distance = round(float(data["distance"]) * 0.001, 3)
                ride_request = RideRequest(
                    user=self.user,
                    pickup_latitude=data["pickup_latitude"],
                    pickup_longitude=data["pickup_longitude"],
                    dropoff_latitude=data["dropoff_latitude"],
                    dropoff_longitude=data["dropoff_longitude"],
                    pickup_address=data["pickup_address"],
                    dropoff_address=data["dropoff_address"],
                    route_polygon=data["polyline"],
                    price=data["price"],
                    distance=distance,
                    vehicle_type=data["vehicle_type"],
                    special_requests=data["details"],
                    isFemaleDriver=data["isFemaleDriver"]
                    # You can set the other fields, such as driver and actual_fare, when the ride is accepted or completed.
                )

                passenger.passenger_status = Passenger.STATUS_PENDING
                passenger.save()
                ride_request.save()
                rating = Rating.objects.create(ride_request=ride_request, passenger=self.user)
                rating.save()
            response_data = {
                "success": True,
                "message": "Ride request created successfully",
                "type": "passenger_created_ride_request",
                "data": {
                    "id": str(ride_request.id),
                    "pickup_latitude": ride_request.pickup_latitude,
                    "pickup_longitude": ride_request.pickup_longitude,
                    "polyline": ride_request.route_polygon,
                    "dropoff_latitude": ride_request.dropoff_latitude,
                    "dropoff_longitude": ride_request.dropoff_longitude,
                    "pickup_address": ride_request.pickup_address,
                    "dropoff_address": ride_request.dropoff_address,
                    "status": ride_request.status,
                    "price": ride_request.price,
                    "distance": ride_request.distance,
                    "vehicle_type": ride_request.vehicle_type,
                    "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                    "details": ride_request.special_requests,
                    "isFemaleDriver": ride_request.isFemaleDriver,
                },
            }

            return response_data
        except Exception as e:
            logger.error(e)
            return {"success": False, "type": "error", "message": str(e)}

    async def cancel_ride_request(self, data):
        try:
            ride_request_id = data["ride_request_id"]
            pending = True

            ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
            if ride_request.status == RideRequest.STATUS_ACCEPTED:
                group_name = cache.get(f"cg_{self.user_id}")
                redis_client.delete(f"cg_{self.user_id}")
                response = {
                    "success": True,
                    "message": "Ride request cancelled successfully",
                    "type": "passenger_cancelled_ride_request",
                    "data": {
                        "id": str(ride_request.id),
                    },
                }
                await self.channel_layer.group_send(
                    group_name,
                    {"type": "driver_accepts_ride_request", "data": response},
                )
                # Driver
                driver_id = ride_request.driver_id
                driver = await database_sync_to_async(Driver.objects.get)(id=driver_id)
                driver_user_id = driver.user_id
                driver_channel_name = cache.get(f"driverconsumer_{driver_user_id}")
                driver.jobDriverStatus = Driver.STATUS_AVAILABLE
                await database_sync_to_async(driver.save)()
                pending = False
                # Discard Passenger and Driver from group

                await self.channel_layer.group_discard(group_name, driver_channel_name)
                await self.channel_layer.group_discard(group_name, self.channel_name)
                await self.channel_layer.group_add("drivers", driver_channel_name)

            # Passenger
            passenger = await database_sync_to_async(Passenger.objects.get)(user_id=self.user_id)
            passenger.passenger_status = Passenger.STATUS_AVAILABLE
            await database_sync_to_async(passenger.save)()

            ride_request.status = RideRequest.STATUS_CANCELED
            await database_sync_to_async(ride_request.save)()

            response_data = {
                "success": True,
                "message": "Ride request cancelled successfully",
                "type": "passenger_cancelled_ride_request",
                "data": {
                    "id": str(ride_request.id),
                    "pickup_latitude": ride_request.pickup_latitude,
                    "pickup_longitude": ride_request.pickup_longitude,
                    "polyline": ride_request.route_polygon,
                    "dropoff_latitude": ride_request.dropoff_latitude,
                    "dropoff_longitude": ride_request.dropoff_longitude,
                    "pickup_address": ride_request.pickup_address,
                    "dropoff_address": ride_request.dropoff_address,
                    "status": ride_request.status,
                    "price": float(ride_request.price),
                    "distance": ride_request.distance,
                    "vehicle_type": ride_request.vehicle_type,
                    "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                    "details": ride_request.special_requests,
                },
            }

            if pending == True:
                await self.channel_layer.group_send(
                    "drivers", {"type": "driver_accepts_ride_request", "data": response_data}
                )

        except Exception as e:
            logger.error(e)
            return {"success": False, "type": "error", "message": str(e)}

        return response_data

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

    def passenger_statusDetails(self, ride_request, driver, driver_details, status):
        driver_user = database_sync_to_async(User.objects.get)(id=driver.user_id)
        return {
            "type": "passenger_status",
            "passenger_status": status,
            "data": {
                "ride_request_info": {
                    "id": str(ride_request.id),
                    "pickup_latitude": ride_request.pickup_latitude,
                    "pickup_longitude": ride_request.pickup_longitude,
                    "polyline": ride_request.route_polygon,
                    "pickup_address": ride_request.pickup_address,
                    "dropoff_address": ride_request.dropoff_address,
                    "dropoff_latitude": ride_request.dropoff_latitude,
                    "dropoff_longitude": ride_request.dropoff_longitude,
                    "vehicle_type": ride_request.vehicle_type,
                    "price": float(ride_request.price),
                    "distance": ride_request.distance,
                    "special_requests": ride_request.special_requests,
                    "status": ride_request.status,
                    "created_at": ride_request.created_at.isoformat(),
                    "isFemaleDriver": ride_request.isFemaleDriver,
                },
                "driver_info": {
                    "driver_id": str(driver.user_id),
                    "driver_status": driver.jobDriverStatus,
                    "driver_name": driver_details.fullname,
                    "driver_profile_pic": driver_details.profile_img.url if driver_details.profile_img else "",
                    "driver_phone_number": driver_details.phone_no if driver_details.phone_no else "",
                    "vehicle_registration_number": driver.vehicle_registration_number
                    if driver.vehicle_registration_number
                    else "",
                    "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                    "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                    "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                    "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
                },
                "passenger_info": {
                    "passenger_id": str(self.user.id),
                    "passenger_name": self.user.fullname,
                    "passenger_phone_number": self.user.phone_no,
                    "passenger_gender": self.user.gender,
                },
            },
        }

    async def driver_arrived_at_pickup(self, event):
        data = event["data"]
        await self.send(json.dumps(data))


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

        cache.set(f"driverconsumer_{self.user_id}", self.channel_name, 86400)

        if driver_status == "enroute_pickup" or driver_status == "in_transit":
            ride_request_id = driver.ride_request
            cache_key = f"cg_{ride_request_id}"

            self.group_name = cache.get(cache_key)
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        else:
            driver.jobDriverStatus = Driver.STATUS_AVAILABLE
            await sync_to_async(driver.save)()
            driver_gender = self.user.gender
            ride_requests = await self.get_pending_ride_requests(type=driver.vehicle_type, driver_gender=driver_gender)
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
                    "polyline": ride_request.route_polygon,
                    "price": float(round(ride_request.price, 2)),
                    "distance": str(ride_request.distance),
                    "vehicle_type": ride_request.vehicle_type if ride_request.vehicle_type else "",
                    "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                    "details": ride_request.special_requests,
                    "isFemaleDriver": ride_request.isFemaleDriver,
                }
                data_list.append(data)
            response = {
                "action": "sending_pending_ride_request",
                "type": "send_pending_ride_request",
                "data": data_list,
            }
            await self.channel_layer.group_add("drivers", self.channel_name)

        await self.accept()

        driverStatus = driver.jobDriverStatus
        archived_messages = []

        if response is not None:
            await self.send(json.dumps(response))

        if driverStatus == Driver.STATUS_ENROUTE_PICKUP:
            archived_messages = await self.get_archived_messages(driver, archived_messages)
            response = await self.get_driver_status(driver, status=Driver.STATUS_ENROUTE_PICKUP)
            await self.send(json.dumps(response))
            await self.send(json.dumps({"type": "archived_messages", "data": archived_messages}))
        elif driverStatus == Driver.STATUS_IN_TRANSIT:
            archived_messages = await self.get_archived_messages(driver, archived_messages)
            response = await self.get_driver_status(driver, status=Driver.STATUS_IN_TRANSIT)
            await self.send(json.dumps(response))
            await self.send(json.dumps({"type": "archived_messages", "data": archived_messages}))
        # elif driverStatus == Driver.STATUS_AVAILABLE:
        #     response = await self.get_driver_status(driver, status=Driver.STATUS_AVAILABLE)
        #     await self.send(json.dumps(response))

    async def get_archived_messages(self, driver, archived_messages):
        ride_request = await database_sync_to_async(RideRequest.objects.filter(driver=driver).latest)("created_at")
        event_key = f"cg_{ride_request.user_id}"
        messages = redis_client.hgetall(event_key)
        for value in messages.values():
            decoded_value = json.loads(value.decode("utf-8"))
            archived_messages.append(decoded_value)

        sorted_messages = sorted(archived_messages, key=lambda msg: datetime.fromisoformat(msg["time"]), reverse=True)
        archived_messages = sorted_messages

        return archived_messages

    async def get_driver_status(self, driver, status):
        ride_request = await database_sync_to_async(RideRequest.objects.filter(driver=driver).latest)("created_at")
        passenger = await database_sync_to_async(User.objects.get)(id=ride_request.user_id)
        if status == Driver.STATUS_ENROUTE_PICKUP or status == Driver.STATUS_IN_TRANSIT:
            response = {
                "type": "driver_status",
                "driver_status": status,
                "data": {
                    "ride_request_info": {
                        "id": str(ride_request.id),
                        "pickup_latitude": ride_request.pickup_latitude,
                        "pickup_longitude": ride_request.pickup_longitude,
                        "polyline": ride_request.route_polygon,
                        "pickup_address": ride_request.pickup_address,
                        "dropoff_address": ride_request.dropoff_address,
                        "dropoff_latitude": ride_request.dropoff_latitude,
                        "dropoff_longitude": ride_request.dropoff_longitude,
                        "vehicle_type": ride_request.vehicle_type,
                        "price": float(ride_request.price),
                        "distance": ride_request.distance,
                        "special_requests": ride_request.special_requests,
                        "status": ride_request.status,
                        "created_at": ride_request.created_at.isoformat(),
                        "isFemaleDriver": ride_request.isFemaleDriver,
                    },
                    "passenger_info": {
                        "passenger_id": str(passenger.id),
                        "passenger_name": passenger.fullname,
                        "passenger_phone_number": passenger.phone_no,
                        "passenger_gender": passenger.gender,
                    },
                    "driver_info": {
                        "driver_id": str(driver.user_id),
                        "driver_status": driver.jobDriverStatus,
                        "driver_name": self.user.fullname,
                        "driver_profile_pic": str(self.user.profile_img.url) if self.user.profile_img else "",
                        "driver_phone_number": self.user.phone_no if self.user.phone_no else "",
                        "vehicle_registration_number": driver.vehicle_registration_number
                        if driver.vehicle_registration_number
                        else "",
                        "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                        "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                        "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                        "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
                    },
                },
            }
        else:
            response = {
                "type": "driver_status",
                "driver_status": status,
                "data": {
                    "ride_request_info": {
                        "id": "",
                        "pickup_latitude": "",
                        "pickup_longitude": "",
                        "polyline": "",
                        "pickup_address": "",
                        "dropoff_address": "",
                        "dropoff_latitude": "",
                        "dropoff_longitude": "",
                        "vehicle_type": "",
                        "price": "",
                        "distance": "",
                        "details": "",
                        "status": "",
                        "created_at": "",
                        "isFemaleDriver": "",
                    },
                    "passenger_info": {
                        "passenger_id": "",
                        "passenger_name": "",
                        "passenger_phone_number": "",
                        "passenger_gender": "",
                    },
                    "driver_info": {
                        "driver_id": str(driver.user_id),
                        "driver_status": driver.jobDriverStatus,
                        "driver_name": self.user.fullname,
                        "driver_profile_pic": str(self.user.profile_img.url) if self.user.profile_img else "",
                        "driver_phone_number": self.user.phone_no if self.user.phone_no else "",
                        "vehicle_registration_number": driver.vehicle_registration_number
                        if driver.vehicle_registration_number
                        else "",
                        "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                        "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                        "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                        "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
                    },
                },
            }

        return response

    async def disconnect(self, close_code):
        driver = await sync_to_async(Driver.objects.get)(user=self.user)

        if driver.jobDriverStatus == Driver.STATUS_ENROUTE_PICKUP or driver.jobDriverStatus == Driver.STATUS_IN_TRANSIT:
            pass
        else:
            driver.jobDriverStatus = Driver.STATUS_UNAVAILABLE
            await sync_to_async(driver.save)()

        await self.channel_layer.group_discard("drivers", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "accept_ride_request":
            result = await self.accept_ride_request(data)
            await self.send(json.dumps(result))
        elif action == "send_chat_message":
            await self.send_chat_message(data)
        elif action == "start_trip":
            result = await self.start_trip(data)
            await self.send(json.dumps(result))
        elif action == "complete_trip":
            result = await self.complete_trip(data)
            await self.send(json.dumps(result))
        elif action == "cancel_ride_request":
            result = await self.cancel_ride_request(data)
            await self.send(json.dumps(result))
        elif action == "arrive_at_pickup":
            await self.arrive_at_pickup(data)

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
        try:
            if event["specialrequestpassenger_id"]:
                user_id = event["specialrequestpassenger_id"]
        except:
            pass
        driver = await sync_to_async(Driver.objects.get)(user=self.user_id)
        ride_request = await database_sync_to_async(RideRequest.objects.filter(driver=driver).latest)("created_at")
        event_key = f"cg_{ride_request.user_id}"
        event_dict = {
            "type": "chat_message",
            "message": event["message"],
            "user_id": user_id,
            "time": datetime.now().isoformat(),
        }
        action = {
            "type": "chat_message",
            "user_id": user_id,
            "message": message,
            "time": datetime.now().isoformat(),
        }
        try:
            if event["event"] == "automated_message":
                event_dict = {
                    "type": "automated_message",
                    "message": event["message"],
                    "user_id": user_id,
                    "time": datetime.now().isoformat(),
                }

                action = {
                    "type": "chat_message",
                    "event": "automated_message",
                    "user_id": user_id,
                    "message": message,
                    "time": datetime.now().isoformat(),
                }
        except:
            pass
        redis_client.hset(name=event_key, key=datetime.now().timestamp(), value=json.dumps(event_dict))
        # TODO letak ni dalam def connect
        # messages = redis_client.hgetall(event_key)
        # archived_messages = []
        # for value in messages.values():
        #     decoded_value = json.loads(value.decode("utf-8"))
        #     archived_messages.append(decoded_value)
        await self.channel_layer.group_send(
            self.group_name,
            action,
        )

    async def chat_message(self, event):
        event_dict = {
            "type": "chat_message",
            "message": event["message"],
            "user_id": event["user_id"],
            "time": event["time"],
        }
        try:
            if event["event"] == "automated_message":
                event_dict = {
                    "type": "automated_message",
                    "message": event["message"],
                    "user_id": event["user_id"],
                    "time": event["time"],
                }
        except:
            pass

        await self.send(json.dumps(event_dict))

    async def add_consumers_to_group(self, group_name, channel_name, passenger_channel_name, data):
        await self.channel_layer.group_add(group_name, channel_name)
        await self.channel_layer.group_add(group_name, passenger_channel_name)
        await self.channel_layer.group_send(group_name, {"type": "driver_accepts_ride_request", "data": data})

    async def accept_ride_request(self, data):
        try:
            ride_request_id = data["ride_request_id"]
            ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)

            driver = await database_sync_to_async(Driver.objects.get)(user=self.user)
            driver_warning_rate = await database_sync_to_async(CancelRateDriver.objects.get)(driver=driver)
            logger.info(f"driver_warning_rate: {driver_warning_rate.warning_rate}")

            if driver_warning_rate.warning_rate > 0:
                hour = driver_warning_rate.warning_rate
                updated_at = driver_warning_rate.updated_at
                waiting_period = hour - (datetime.now().timestamp() - updated_at.timestamp()) / 3600
                waiting_period = round(waiting_period)
                waiting_period = int(waiting_period)
                message = (
                    f"You have been blocked from accepting any ride requests. Please wait for {waiting_period} hour(s)."
                )

                if waiting_period > 0:
                    return {
                        "success": True,
                        "type": "disable_driver",
                        "message": message,
                    }

            if ride_request.status != RideRequest.STATUS_PENDING:
                return {"success": False, "message": "Ride request is not pending"}

            driver_ewallet = await database_sync_to_async(DriverEwallet.objects.get)(user=self.user)

            commission_amount = get_commission_amount(
                price=ride_request.price, role=self.user.role, distance=ride_request.distance
            )
            if commission_amount > driver_ewallet.balance:
                return {"success": False, "message": "Insufficient balance"}

            driver = await database_sync_to_async(lambda: self.user.driver)()
            ride_request.status = RideRequest.STATUS_ACCEPTED
            ride_request.driver = driver

            rating = await database_sync_to_async(Rating.objects.get)(ride_request=ride_request)
            rating.driver = driver
            await database_sync_to_async(rating.save)()

            driver.jobDriverStatus = Driver.STATUS_ENROUTE_PICKUP
            driver.ride_request = ride_request.user_id
            await database_sync_to_async(ride_request.save)()
            await database_sync_to_async(driver.save)()

            passenger = await database_sync_to_async(Passenger.objects.get)(user_id=ride_request.user_id)
            passenger.passenger_status = Passenger.STATUS_ACCEPTED
            await database_sync_to_async(passenger.save)()
            passenger_user = await database_sync_to_async(User.objects.get)(id=passenger.user_id)

            await self.channel_layer.group_discard("drivers", self.channel_name)
            # Add both consumers to the group
            self.group_name = f"{ride_request.id}{driver.user_id}"
            cache.set(f"cg_{ride_request.user_id}", self.group_name, None)

            driverinfo = {
                "driver_id": str(driver.user_id),
                "driver_status": driver.jobDriverStatus,
                "driver_name": driver.user.fullname,
                "driver_profile_pic": str(driver.user.profile_img.url) if driver.user.profile_img else "",
                "driver_phone_number": driver.user.phone_no if driver.user.phone_no else "",
                "vehicle_registration_number": driver.vehicle_registration_number
                if driver.vehicle_registration_number
                else "",
                "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
            }
            rideRequestinfo = {
                "id": str(ride_request.id),
                "pickup_latitude": ride_request.pickup_latitude,
                "pickup_longitude": ride_request.pickup_longitude,
                "dropoff_latitude": ride_request.dropoff_latitude,
                "dropoff_longitude": ride_request.dropoff_longitude,
                "pickup_address": ride_request.pickup_address,
                "dropoff_address": ride_request.dropoff_address,
                "status": ride_request.status,
                "polyline": ride_request.route_polygon,
                "price": float(round(ride_request.price, 2)),
                "distance": ride_request.distance,
                "vehicle_type": ride_request.vehicle_type if ride_request.vehicle_type else "",
                "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                "details": ride_request.special_requests if ride_request.special_requests else "",
                "isFemaleDriver": ride_request.isFemaleDriver,
            }

            passenger_info = {
                "passenger_id": str(passenger.user_id),
                "passenger_name": passenger_user.fullname,
                "passenger_phone_number": passenger_user.phone_no,
                "passenger_gender": passenger_user.gender,
            }

            response_data_to_passenger = {
                "success": True,
                "message": "Ride request accepted successfully",
                "type": "driver_passenger_ride_request_accepted",
                "data": {
                    "driver_info": driverinfo,
                    "ride_request_info": rideRequestinfo,
                    "passenger_info": passenger_info,
                },
            }

            passenger_channel_name = cache.get(f"passengerconsumer_{ride_request.user_id}")
            if passenger_channel_name:
                await self.add_consumers_to_group(
                    self.group_name, self.channel_name, passenger_channel_name, response_data_to_passenger
                )

            important_messages = {
                "message": f"\u26A0 IMPORTANT REMINDER: Your safety is our top priority. We remind all passengers and drivers to treat each other with respect and kindness. Any form of sexual harassment or inappropriate behavior will not be tolerated. If you experience any issues during your ride, please contact our support team immediately. Thank you for helping us maintain a safe and respectful community.",
                "event": "important_message",
            }
            await self.send_chat_message(important_messages)

            if ride_request.special_requests is not None and ride_request.special_requests != "":
                details = {
                    "message": f"{ride_request.special_requests}",
                    "specialrequestpassenger_id": str(ride_request.user_id),
                }
                await self.send_chat_message(details)

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
        except RideRequest.DoesNotExist as e:
            logger.error(e)
            return {"success": False, "type": "error", "message": str(e)}
        except Exception as e:
            logger.error(e)
            tb = traceback.format_exc()
            return {"success": False, "type": "error", "message": str(e), "traceback": tb}

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

            passenger = await database_sync_to_async(Passenger.objects.get)(user_id=ride_request.user_id)
            passenger.passenger_status = Passenger.STATUS_IN_PROGRESS
            await database_sync_to_async(passenger.save)()

            response_data = {
                "success": True,
                "type": "driver_started_trip",
                "message": "Ride request starts successfully",
                "data": {
                    "id": str(ride_request.id),
                    "status": ride_request.status,
                },
            }

            cache_key = f"cg_{ride_request.user_id}"

            self.group_name = cache.get(cache_key)
            await self.channel_layer.group_send(self.group_name, {"type": "driver_start_trip", "data": response_data})

            return response_data

        except RideRequest.DoesNotExist:
            return {"success": False, "message": "Ride request does not exist"}
        except Exception as e:
            logger.error(e)
            tb = traceback.format_exc()
            return {"success": False, "type": "error", "message": str(e), "traceback": tb}

    async def remove_consumers_to_group(self, group_name, channel_name, passenger_channel_name, response):
        try:
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

            cache.delete(f"cg_{ride_request.user_id}")
        except Exception as e:
            logger.error(e)
            raise e

    async def complete_trip(self, data):
        try:
            ride_request_id = data["ride_request_id"]
            ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
            ride_request.status = RideRequest.STATUS_COMPLETED
            ride_request.dropoff_time = datetime.now()
            await database_sync_to_async(ride_request.save)()

            commission_paid = await database_sync_to_async(CommissionHistory.objects.create)(
                driver=self.user,
                commission_amount=get_commission_amount(
                    price=ride_request.price, role=self.user.role, distance=ride_request.distance
                ),
            )
            await database_sync_to_async(commission_paid.save)()
            commission_amount = commission_paid.commission_amount
            driver_ewallet = await database_sync_to_async(DriverEwallet.objects.get)(user=self.user)

            driver_ewallet.balance -= round(commission_amount, 2)
            await database_sync_to_async(driver_ewallet.save)()
            await database_sync_to_async(DriverEarning.objects.create)(
                driver=self.user,
                earning_amount=ride_request.price - commission_amount,
                ride_request_id=ride_request,
            )

            driver = await database_sync_to_async(lambda: self.user.driver)()
            driver.jobDriverStatus = Driver.STATUS_AVAILABLE
            await database_sync_to_async(driver.save)()

            passenger = await database_sync_to_async(Passenger.objects.get)(user_id=ride_request.user_id)
            passenger.passenger_status = Passenger.STATUS_AVAILABLE
            await database_sync_to_async(passenger.save)()

            passenger_channel_name = cache.get(f"passengerconsumer_{ride_request.user_id}")
            if passenger_channel_name:
                await self.remove_consumers_to_group(self.group_name, self.channel_name, passenger_channel_name, data)

            event_key = f"cg_{ride_request.user_id}"
            message = redis_client.delete(event_key)

            response_data = {
                "success": True,
                "message": "Ride request completed successfully",
                "type": "driver_completed_ride_request_notifications",
                "data": {
                    "id": str(ride_request.id),
                    "status": ride_request.status,
                    "commission_amount": float(round(commission_amount, 2)),
                    "earning_amount": float(round((ride_request.price - commission_amount), 2)),
                },
            }

            # sending back available ride request lists
            driver_gender = self.user.gender
            ride_requests = await self.get_pending_ride_requests(type=driver.vehicle_type, driver_gender=driver_gender)
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
                    "polyline": ride_request.route_polygon,
                    "price": float(round(ride_request.price, 2)),
                    "distance": str(ride_request.distance),
                    "vehicle_type": ride_request.vehicle_type if ride_request.vehicle_type else "",
                    "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                    "details": ride_request.special_requests,
                    "isFemaleDriver": ride_request.isFemaleDriver,
                }
                data_list.append(data)

            send_ride_request = {
                "action": "sending_pending_ride_request",
                "type": "send_pending_ride_request",
                "data": data_list,
            }

            await self.send(json.dumps(send_ride_request))

            return response_data

        except Exception as e:
            logger.error(e)
            tb = traceback.format_exc()
            return {"success": False, "type": "error", "message": str(e), "traceback": tb}

    async def cancel_ride_request(self, data):
        try:
            ride_request_id = data["ride_request_id"]
            cancel_reason = data["cancel_reason"]

            ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
            if ride_request.status == RideRequest.STATUS_ACCEPTED:
                cache_key = f"cg_{ride_request.user_id}"
                group_name = cache.get(cache_key)
                redis_client.delete(cache_key)
                response = {
                    "success": True,
                    "message": "Ride request cancelled successfully",
                    "type": "driver_cancelled_ride_request",
                    "data": {
                        "id": str(ride_request.id),
                    },
                }
                await self.channel_layer.group_send(
                    group_name,
                    {"type": "driver_accepts_ride_request", "data": response},
                )
                # Driver

                driver_id = ride_request.driver_id
                driver = await database_sync_to_async(Driver.objects.get)(id=driver_id)
                if driver.jobDriverStatus == Driver.STATUS_ENROUTE_PICKUP:
                    driver_cancel_rate = await database_sync_to_async(CancelRateDriver.objects.get)(driver=driver)
                    if driver_cancel_rate:
                        driver_cancel_rate.cancel_rate += 1
                        await database_sync_to_async(driver_cancel_rate.update_warning_rate)()
                        await database_sync_to_async(driver_cancel_rate.save)()

                driver.jobDriverStatus = Driver.STATUS_AVAILABLE
                await database_sync_to_async(driver.save)()

                # Passenger
                passenger = await database_sync_to_async(Passenger.objects.get)(user_id=ride_request.user_id)
                passenger.passenger_status = Passenger.STATUS_AVAILABLE
                await database_sync_to_async(passenger.save)()
                passenger_channel_name = cache.get(f"passengerconsumer_{ride_request.user_id}")

                # Discard Passenger and Driver from group

                await self.channel_layer.group_discard(group_name, self.channel_name)
                await self.channel_layer.group_discard(group_name, passenger_channel_name)
                await self.channel_layer.group_add("drivers", self.channel_name)

            ride_request.status = RideRequest.STATUS_CANCELED
            ride_request.cancel_reason = cancel_reason
            await database_sync_to_async(ride_request.save)()

            response_data = {
                "success": True,
                "message": "Ride request cancelled successfully",
                "type": "passenger_cancelled_ride_request",
                "data": {
                    "id": str(ride_request.id),
                    "pickup_latitude": ride_request.pickup_latitude,
                    "pickup_longitude": ride_request.pickup_longitude,
                    "polyline": ride_request.route_polygon,
                    "dropoff_latitude": ride_request.dropoff_latitude,
                    "dropoff_longitude": ride_request.dropoff_longitude,
                    "pickup_address": ride_request.pickup_address,
                    "dropoff_address": ride_request.dropoff_address,
                    "status": ride_request.status,
                    "price": float(ride_request.price),
                    "distance": ride_request.distance,
                    "vehicle_type": ride_request.vehicle_type,
                    "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                    "details": ride_request.special_requests,
                    "isFemaleDriver": ride_request.isFemaleDriver,
                },
            }
            driver_gender = self.user.gender
            ride_requests = await self.get_pending_ride_requests(type=driver.vehicle_type, driver_gender=driver_gender)
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
                    "polyline": ride_request.route_polygon,
                    "price": float(round(ride_request.price, 2)),
                    "distance": str(ride_request.distance),
                    "vehicle_type": ride_request.vehicle_type if ride_request.vehicle_type else "",
                    "created_at": ride_request.created_at.isoformat() if ride_request.created_at else "",
                    "details": ride_request.special_requests,
                    "isFemaleDriver": ride_request.isFemaleDriver,
                }
                data_list.append(data)

            send_ride_request = {
                "action": "sending_pending_ride_request",
                "type": "send_pending_ride_request",
                "data": data_list,
            }

            await self.send(json.dumps(send_ride_request))

        except Exception as e:
            logger.error(e)
            tb = traceback.format_exc()
            return {"success": False, "type": "error", "message": str(e), "traceback": tb}

        return response_data

    async def arrive_at_pickup(self, data):
        ride_request_id = data["ride_request_id"]
        ride_request = await database_sync_to_async(RideRequest.objects.get)(id=ride_request_id)
        cache_key = f"cg_{ride_request.user_id}"
        group_name = cache.get(cache_key)
        response = {
            "success": True,
            "type": "driver_arrived_at_pickup",
            "message": "Driver arrived at pickup location",
        }
        await self.channel_layer.group_send(
            group_name,
            {"type": "driver_arrived_at_pickup", "data": response},
        )

    async def driver_arrived_at_pickup(self, event):
        pass

    async def driver_accepts_ride_request(self, event):
        await self.send(json.dumps(event["data"]))

    async def send_new_ride_request(self, event):
        original_data = event["data"]

        data = OrderedDict()
        data["success"] = original_data["success"]
        data["type"] = "passenger_created_ride_request"
        for key, value in original_data.items():
            if key not in ["success", "message"]:
                data[key] = value
        driver_gender = self.user.gender
        driver = await sync_to_async(lambda: self.user.driver)()
        driver_vehicle_type = driver.vehicle_type
        if data["data"]["vehicle_type"] == "4pax" and driver_vehicle_type == "4pax":
            if data["data"]["isFemaleDriver"] == True and driver_gender == "female":
                await self.send(json.dumps(data))
            elif data["data"]["isFemaleDriver"] == True and driver_gender == "male":
                pass
            elif data["data"]["isFemaleDriver"] == False:
                await self.send(json.dumps(data))
        elif driver_vehicle_type == "6pax":
            if data["data"]["isFemaleDriver"] == True and driver_gender == "female":
                await self.send(json.dumps(data))
            elif data["data"]["isFemaleDriver"] == True and driver_gender == "male":
                pass
            elif data["data"]["isFemaleDriver"] == False:
                await self.send(json.dumps(data))
        elif data["data"]["vehicle_type"] == "6pax" and driver_vehicle_type == "4pax":
            pass

        # Create a new ordered dictionary and add the keys in the desired order


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
        action = data.get("action", "")
        if action == "location_update":
            latitude = data.get("latitude", 0)
            longitude = data.get("longitude", 0)

            # Send location data to the passenger
            await self.channel_layer.group_send(
                self.user_id,
                {"type": "location_update", "latitude": latitude, "longitude": longitude},
            )

    async def location_update(self, event):
        response = {
            "success": True,
            "type": event["type"],
            "data": {
                "latitude": event["latitude"],
                "longitude": event["longitude"],
            },
        }
        await self.send(json.dumps(response))
