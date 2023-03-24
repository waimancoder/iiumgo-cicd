from .models import RideRequest
from asgiref.sync import sync_to_async


class RideRequestMixin:
    async def send_pending_ride_requests_to_drivers(self):
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

        await self.channel_layer.group_send("drivers", {"type": "send_pending_ride_request", "data": data_list})

    @sync_to_async
    def get_pending_ride_requests(self):
        return list(RideRequest.objects.filter(status="pending"))