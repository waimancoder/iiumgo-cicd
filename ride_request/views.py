import base64
import random
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from ride_request.pricing import get_pricing
from rides.models import Driver
from .models import PopularLocation, RideRequest
from .serializers import CoordinateSerializer, PopularLocationSerializer, RideRequestSerializer
from rest_framework.pagination import PageNumberPagination


# Create your views here.
class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"


class RideRequestHistoryView(generics.ListAPIView):
    serializer_class = RideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        return RideRequest.objects.filter(user_id=user_id, status=RideRequest.STATUS_COMPLETED).order_by("-created_at")

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
                    "count": queryset.count(),
                    "next": self.paginator.get_next_link(),
                    "previous": self.paginator.get_next_link(),
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
