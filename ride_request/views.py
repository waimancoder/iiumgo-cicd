from django.contrib.auth.models import User
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


class PopularLocationView(generics.ListAPIView):
    serializer_class = PopularLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = PopularLocation.objects.all()
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            paginated_queryset = self.paginate_queryset(queryset)

            print(paginated_queryset)

            serializer = self.get_serializer(paginated_queryset, many=True)
            locations = serializer.data

            # Replace any 'null' values with empty strings
            for location in locations:
                for key, value in location.items():
                    if value is None:
                        location[key] = ""

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "popular_locations": locations,
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
