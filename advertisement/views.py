import base64
from os import name
import random
import uuid
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import render

from rest_framework import generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from advertisement.models import Advertisement, TodoTask
from advertisement.serializers import (
    AdvertisementSerializer,
    ResponseSchema200,
    ResponseSchema500,
    TodoTaskChangeStatusSerializer,
    TodoTaskSerializer,
)
from mytaxi.scheme import KnoxTokenScheme
from drf_spectacular.utils import extend_schema


# Create your views here.
class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"


class AdvertisementView(generics.GenericAPIView):
    serializer_class = AdvertisementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Advertisement.objects.all().order_by("id")
        return queryset

    @extend_schema(
        responses={200: ResponseSchema200(context={"data": AdvertisementSerializer}), 500: ResponseSchema500},
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            paginated_queryset = self.paginate_queryset(queryset)
            serializer = self.get_serializer(queryset, many=True)
            instances = list(paginated_queryset)
            data = serializer.data

            # Replace any 'null' values with empty strings
            for datum in data:
                for key, value in datum.items():
                    if value is None:
                        datum[key] = ""

            for i, instance in enumerate(instances):
                data[i]["image"] = instance.image.url if instance.image else ""

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": data,
            }

            return Response(response, status=status.HTTP_200_OK)
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

    @extend_schema(
        responses={200: ResponseSchema200(context={"data": AdvertisementSerializer}), 500: ResponseSchema500},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advertisement = serializer.save()

        return Response(
            {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "id": advertisement.id,
                    "title": advertisement.title,
                    "details": advertisement.details,
                    "advertiser": advertisement.advertiser,
                    "phone_no": advertisement.phone_no,
                    "return_url": advertisement.return_url,
                    "rental_time_from": advertisement.rental_time_from,
                    "rental_time_to": advertisement.rental_time_to,
                    "image": advertisement.image.url if advertisement.image else "",
                    "is_valid": advertisement.is_valid,
                },
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ads_id = request.data.get("id", None)
        if not ads_id:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "message": "id is required for updating",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            advertisement = Advertisement.objects.get(id=ads_id)
        except Advertisement.DoesNotExist:
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
                advertisement.image = image_file
            else:
                setattr(advertisement, field, serializer.validated_data[field])

        advertisement.save()

        return Response(
            {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "id": advertisement.id,
                    "title": advertisement.title,
                    "details": advertisement.details,
                    "advertiser": advertisement.advertiser,
                    "phone_no": advertisement.phone_no,
                    "return_url": advertisement.return_url,
                    "rental_time_from": advertisement.rental_time_from,
                    "rental_time_to": advertisement.rental_time_to,
                    "image": advertisement.image.url if advertisement.image else "",
                    "is_valid": advertisement.is_valid,
                },
            },
            status=status.HTTP_200_OK,
        )


class TodoTaskAPI(generics.GenericAPIView):
    serializer_class = TodoTaskSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = TodoTask.objects.all()
        return queryset

    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)

            data = serializer.data
            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": data,
            }
            return Response(response, status=status.HTTP_200_OK)

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

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            task = serializer.save()

            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "data": {"id": task.id, "name": task.name, "description": task.description, "status": task.status},
                },
                status=status.HTTP_200_OK,
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


class TodoTaskChangeStatusAPI(generics.GenericAPIView):
    serializer_class = TodoTaskChangeStatusSerializer
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post"]
    lookup_field = "id"

    def get(self, request, id, *args, **kwargs):
        try:
            task = TodoTask.objects.get(id=id)
            serializer = self.get_serializer(task)

            data = serializer.data
            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": data,
            }
            return Response(response, status=status.HTTP_200_OK)

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

    def post(self, request, id, *args, **kwargs):
        try:
            task = TodoTask.objects.get(id=id)  # Retrieve the task by ID
            serializer = self.get_serializer(instance=task, data=request.data)
            serializer.is_valid(raise_exception=True)
            task = serializer.save()

            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "data": {"id": task.id, "name": task.name, "description": task.description, "status": task.status},
                },
                status=status.HTTP_200_OK,
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
