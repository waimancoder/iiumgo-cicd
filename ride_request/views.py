import base64
import random
from django.core.files.base import ContentFile
from django.shortcuts import render
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from django.db.models import Q
import ride_request
from ride_request.pricing import get_pricing
from rides.models import Driver
from .models import CancelRateDriver, PopularLocation, Rating, RideRequest
from .serializers import (
    CoordinateSerializer,
    DriverCancelRateSerializer,
    DriverRideRequestSerializer,
    PopularLocationSerializer,
    RatingSerializer,
    RideRequestSerializer,
)
from rest_framework.pagination import PageNumberPagination
import logging

logger = logging.getLogger(__name__)


# Create your views here.
class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"


class RideRequestHistoryView(generics.ListAPIView):
    serializer_class = RideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        canceled_requests = RideRequest.objects.filter(
            Q(user_id=user_id) & Q(status=RideRequest.STATUS_CANCELED)
        ).order_by("-created_at")
        completed_requests = RideRequest.objects.filter(
            Q(user_id=user_id), Q(status=RideRequest.STATUS_COMPLETED)
        ).order_by("-created_at")
        requests = canceled_requests | completed_requests
        return requests

    def list(self, request, *args, **kwargs):
        try:
            user_id = self.kwargs["user_id"]
            queryset = self.get_queryset()
            paginated_queryset = self.paginate_queryset(queryset)
            serializer = self.get_serializer(paginated_queryset, many=True)
            data = []
            for ride_request in serializer.data:
                if ride_request["status"] == RideRequest.STATUS_COMPLETED:
                    ride_request_info = {
                        "id": ride_request["id"],
                        "status": ride_request["status"],
                        "pickup_latitude": ride_request["pickup_latitude"],
                        "pickup_longitude": ride_request["pickup_longitude"],
                        "dropoff_latitude": ride_request["dropoff_latitude"],
                        "dropoff_longitude": ride_request["dropoff_longitude"],
                        "pickup_address": ride_request["pickup_address"],
                        "dropoff_address": ride_request["dropoff_address"],
                        "pickup_time": ride_request["pickup_time"] if ride_request["pickup_time"] != "" else None,
                        "dropoff_time": ride_request["dropoff_time"],
                        "polyline": ride_request["polyline"],
                        "price": ride_request["price"],
                        "distance": ride_request["distance"],
                        "created_at": ride_request["created_at"],
                    }
                    driver_info = {
                        "driver_name": ride_request["driver_name"],
                        "vehicle_registration_number": ride_request["vehicle_registration_number"],
                        "vehicle_manufacturer": ride_request["vehicle_manufacturer"],
                        "vehicle_model": ride_request["vehicle_model"],
                        "vehicle_color": ride_request["vehicle_color"],
                        "vehicle_type": ride_request["vehicle_type"],
                    }
                    rating_info = {
                        "rating_id": ride_request["rating_id"],
                        "rating": int(ride_request["rating"]) if ride_request["rating"] else None,
                        "israted": ride_request["israted"],
                    }
                    history = {
                        "ride_request_info": ride_request_info,
                        "driver_info": driver_info,
                        "rating_info": rating_info,
                    }
                    data.append(history)
                else:
                    ride_request_info = {
                        "id": ride_request["id"],
                        "status": ride_request["status"],
                        "pickup_latitude": ride_request["pickup_latitude"],
                        "pickup_longitude": ride_request["pickup_longitude"],
                        "dropoff_latitude": ride_request["dropoff_latitude"],
                        "dropoff_longitude": ride_request["dropoff_longitude"],
                        "pickup_address": ride_request["pickup_address"],
                        "dropoff_address": ride_request["dropoff_address"],
                        "pickup_time": None,
                        "dropoff_time": None,
                        "polyline": ride_request["polyline"],
                        "price": ride_request["price"],
                        "distance": ride_request["distance"],
                        "created_at": ride_request["created_at"],
                    }
                    driver_info = {
                        "driver_name": "",
                        "vehicle_registration_number": "",
                        "vehicle_manufacturer": "",
                        "vehicle_model": "",
                        "vehicle_color": "",
                        "vehicle_type": "",
                    }
                    rating_info = {
                        "rating_id": ride_request["rating_id"],
                        "rating": int(ride_request["rating"]) if ride_request["rating"] else None,
                        "israted": ride_request["israted"],
                    }
                    history = {
                        "ride_request_info": ride_request_info,
                        "driver_info": None,
                        "rating_info": None,
                    }
                    data.append(history)

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "user_id": user_id,
                    "history": data,
                },
            }
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            if str(e) == "Invalid page.":
                response = {
                    "status": True,
                    "statusCode": status.HTTP_200_OK,
                    "data": {
                        "user_id": user_id,
                        "history": [],
                    },
                }
                return Response(response, status=status.HTTP_200_OK)
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": "Please Contact Server Admin",
                    "traceback": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DriverRideRequestHistoryView(generics.ListAPIView):
    serializer_class = DriverRideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        driver_id = Driver.objects.get(user_id=user_id).id
        canceled_requests = RideRequest.objects.filter(
            Q(driver_id=driver_id) & Q(status=RideRequest.STATUS_CANCELED)
        ).order_by("-created_at")
        completed_requests = RideRequest.objects.filter(
            Q(driver_id=driver_id) & Q(status=RideRequest.STATUS_COMPLETED)
        ).order_by("-created_at")
        requests = canceled_requests | completed_requests

        return requests

    def list(self, request, *args, **kwargs):
        try:
            user_id = self.kwargs["user_id"]
            queryset = self.get_queryset()
            paginated_queryset = self.paginate_queryset(queryset)

            print(paginated_queryset)

            serializer = self.get_serializer(paginated_queryset, many=True)

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "user_id": user_id,
                    "history": serializer.data,
                },
            }
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": "Please Contact Server Admin",
                    "traceback": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FareEstimationView(generics.GenericAPIView):
    serializer_class = CoordinateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        distance = serializer.validated_data["distance"]
        pickup_latitude = serializer.validated_data["pickup_latitude"]
        pickup_longitude = serializer.validated_data["pickup_longitude"]
        dropoff_latitude = serializer.validated_data["dropoff_latitude"]
        dropoff_longitude = serializer.validated_data["dropoff_longitude"]
        price = get_pricing(pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude, role, distance)
        driver_count_4seater = Driver.objects.filter(
            jobDriverStatus=Driver.STATUS_AVAILABLE, vehicle_type=Driver.TYPE_4SEATER
        ).count()
        driver_count_6seater = Driver.objects.filter(
            jobDriverStatus=Driver.STATUS_AVAILABLE, vehicle_type=Driver.TYPE_6SEATER
        ).count()
        driver_count = {"4seater": driver_count_4seater, "6seater": driver_count_6seater}
        price["currency"] = "MYR"
        data = {"price": price, "driver_count": driver_count}

        return Response({"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK)


class PopularLocationView(generics.GenericAPIView):
    serializer_class = PopularLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = PopularLocation.objects.all().order_by("id")
        return queryset

    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            paginated_queryset = self.paginate_queryset(queryset)
            serializer = self.get_serializer(paginated_queryset, many=True)
            instances = list(paginated_queryset)
            locations = serializer.data

            # Replace any 'null' values with empty strings
            for location in locations:
                for key, value in location.items():
                    if value is None:
                        location[key] = ""

            for i, location in enumerate(locations):
                image = instances[i].image
                if image:
                    location["image"] = image.url
                else:
                    location["image"] = ""

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": locations,
            }
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": "Please Contact Server Admin",
                    "traceback": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        address = serializer.validated_data["address"]
        latitude = serializer.validated_data["latitude"]
        longitude = serializer.validated_data["longitude"]
        subLocality = serializer.validated_data["subLocality"]
        locality = serializer.validated_data["locality"]
        image = serializer.validated_data["image"]
        image_file = None
        if image:
            # Decode the base64 string into binary image data
            random_number = random.randint(0, 10)
            format, imgstr = image.split(";base64,")
            ext = format.split("/")[-1]
            image_file = ContentFile(base64.b64decode(imgstr), name=f"popular_location_{random_number}.{ext}")

        popular_location = PopularLocation.objects.create(
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            image=image_file,
            subLocality=subLocality,
            locality=locality,
        )
        return Response(
            {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "id": popular_location.id,
                    "name": popular_location.name,
                    "address": popular_location.address,
                    "latitude": popular_location.latitude,
                    "longitude": popular_location.longitude,
                    "subLocality": popular_location.subLocality,
                    "locality": popular_location.locality,
                    "image": popular_location.image.url if popular_location.image else "",
                },
            },
            status=status.HTTP_200_OK,
        )

    # put method
    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location_name = request.data.get("name", None)
        if not location_name:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "message": "Location name is required for updating",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            popular_location = PopularLocation.objects.get(name=location_name)
        except PopularLocation.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "message": "Location not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        for field in serializer.validated_data:
            if field == "image" and serializer.validated_data[field]:
                # Decode the base64 string into binary image data
                random_number = random.randint(0, 10)
                format, imgstr = serializer.validated_data[field].split(";base64,")
                ext = format.split("/")[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f"popular_location_{random_number}.{ext}")
                popular_location.image = image_file
            else:
                setattr(popular_location, field, serializer.validated_data[field])

        popular_location.save()

        return Response(
            {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "id": popular_location.id,
                    "name": popular_location.name,
                    "address": popular_location.address,
                    "latitude": popular_location.latitude,
                    "longitude": popular_location.longitude,
                    "subLocality": popular_location.subLocality,
                    "locality": popular_location.locality,
                    "image": popular_location.image.url if popular_location.image else "",
                },
            },
            status=status.HTTP_200_OK,
        )


class DriverCancelRate(generics.GenericAPIView):
    serializer_class = DriverCancelRateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = self.request.user
            driver = Driver.objects.get(user=user)
            driver_cancel_rate = CancelRateDriver.objects.get(driver=driver)
            if driver_cancel_rate:
                serializer = self.get_serializer(driver_cancel_rate)
                return Response(
                    {
                        "success": True,
                        "statusCode": status.HTTP_200_OK,
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "statusCode": status.HTTP_404_NOT_FOUND,
                        "message": "Driver cancel rate not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            print(e)
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": "Please Contact Server Admin",
                    "traceback": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, *args, **kwargs):
        try:
            user = self.request.user
            driver = Driver.objects.get(user=user)
            driver_cancel_rate = CancelRateDriver.objects.get(driver=driver)
            if driver_cancel_rate:
                driver_cancel_rate.cancel_rate += 1
                driver_cancel_rate.update_warning_rate()
                driver_cancel_rate.save()
                serializer = self.get_serializer(driver_cancel_rate)
                return Response(
                    {
                        "success": True,
                        "statusCode": status.HTTP_200_OK,
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "statusCode": status.HTTP_404_NOT_FOUND,
                        "message": "Driver cancel rate not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": "Please Contact Server Admin",
                    "traceback": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RatingAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RatingSerializer

    def get(self, request, *args, **kwargs):
        id = self.kwargs.get("ride_request_id")
        try:
            ride_request = RideRequest.objects.get(id=id)
            rating = Rating.objects.get(ride_request=ride_request)
            serializer = self.get_serializer(rating)
            response = serializer.data
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "data": {
                        "ride_request_id": response["id"],
                        "rating": response["rating"],
                        "comment": response["comment"] if response["comment"] else "",
                        "isRated": response["isRated"],
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "message": str(e),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    def post(self, request, *args, **kwargs):
        id = self.kwargs.get("ride_request_id")
        try:
            ride_request = RideRequest.objects.get(id=id)
            rating = Rating.objects.get(ride_request=ride_request)
            rating.rating = request.data.get("rating", rating.rating)
            rating.isRated = True
            rating.comment = request.data.get("comment", rating.comment)
            rating.save()
            serializer = self.get_serializer(rating, data=request.data)
            serializer.is_valid(raise_exception=True)
            response = serializer.data
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "data": {
                        "ride_request_id": response["id"],
                        "rating": response["rating"],
                        "comment": response["comment"] if response["comment"] else "",
                        "isRated": response["isRated"],
                    },
                },
                status=status.HTTP_200_OK,
            )
        except serializers.ValidationError as e:
            for key in e.detail.keys():
                error_message = e.detail[key][0].__str__()

            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "message": error_message,
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "message": str(e),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
