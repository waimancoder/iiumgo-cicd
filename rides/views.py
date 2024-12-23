from rest_framework import exceptions
from rest_framework.metadata import SimpleMetadata
from ride_request.models import Passenger
from user_account.models import User
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import generics, permissions, status, serializers, mixins
from .serializers import (
    DriverIdConfirmationSerializer,
    DriverLicenseSerializer,
    DriverStatusSerializer,
    DriverVehicleInfo,
    LocationSerializer,
    PassengerStatusSerializer,
    UserDriverDetailsSerializer,
    DriverJobStatusSerializer,
)
from .models import Driver, Location
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.http import Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.conf import settings


User = get_user_model


class CustomMetadata(SimpleMetadata):
    def determine_metadata(self, request, view):
        metadata = super().determine_metadata(request, view)
        upper_methods = [method.upper() for method in view.http_method_names]
        if "PUT" in upper_methods:
            actions = {}
            for field_name, field in view.serializer_class().get_fields().items():
                actions[field_name] = {
                    "type": field.__class__.__name__,
                    "required": getattr(field, "required", False),
                    "read_only": getattr(field, "read_only", False),
                    "label": getattr(field, "label", ""),
                }
            metadata["actions"] = {"PUT": actions}
        return metadata


class LocationDetailView(generics.RetrieveUpdateAPIView, mixins.ListModelMixin, mixins.CreateModelMixin):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    lookup_field = "name"

    def get(self, request, *args, **kwargs):
        try:
            if "name" in kwargs:
                return self.retrieve(request, *args, **kwargs)
            else:
                return self.list(request, *args, **kwargs)
        except Http404:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        response_data = {"status": "OK", "statusCode": status.HTTP_200_OK, "data": serializer.data}
        return Response(response_data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response_data = {"status": "OK", "statusCode": status.HTTP_200_OK, "data": serializer.data}
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            return self.create(request, *args, **kwargs)
        except ValidationError as e:
            return Response(
                {"status": "Bad Request", "statusCode": status.HTTP_400_BAD_REQUEST, "detail": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_data = {"status": "CREATED", "statusCode": status.HTTP_201_CREATED, "data": serializer.data}
        return Response(response_data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response_data = {"status": "OK", "statusCode": status.HTTP_200_OK, "data": serializer.data}

        return Response(response_data, status=status.HTTP_200_OK)


class DriverLicenseViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverLicenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "put", "patch", "delete", "options"]
    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = []
        for driver in serializer.data:
            front = driver["driver_license_img_front"]
            back = driver["driver_license_img_back"]
            if not front:
                front = ""
            if not back:
                back = ""
            if not driver["driver_license_expiry_date"]:
                driver["driver_license_expiry_date"] = ""
            data.append(
                {
                    "user_id": driver["user_id"],
                    "driver_license_expiry_date": driver["driver_license_expiry_date"],
                    "driver_license_img_front": settings.MEDIA_URL + str(front) if front else "",
                    "driver_license_img_back": settings.MEDIA_URL + str(back) if back else "",
                }
            )
        return Response({"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def driver_license_img(self, request, user_id=None):
        try:
            driver = self.get_object()
            front_url = ""
            try:
                front_url = settings.MEDIA_URL + str(driver.driver_license_img_front.url)
            except ValueError:
                pass
            back_url = ""
            try:
                back_url = settings.MEDIA_URL + str(driver.driver_license_img_back.url)
            except ValueError:
                pass
            data = {
                "user_id": driver.user_id if driver.user_id else "",
                "driver_license_expiry_date": driver.driver_license_expiry_date
                if driver.driver_license_expiry_date
                else "",
                "driver_license_img_front": front_url,
                "driver_license_img_back": back_url,
            }
            return Response(
                {"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK
            )
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": "Details not found",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["put"])
    def updateDriverLicense(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_data = {
            "status": "OK",
            "statusCode": status.HTTP_200_OK,
            "data": {
                "user_id": serializer.data["user_id"] if serializer.data["user_id"] else "",
                "driver_license_expiry_date": str(serializer.data["driver_license_expiry_date"])
                if serializer.data["driver_license_expiry_date"]
                else "",
                "driver_license_img_front": settings.MEDIA_URL + str(serializer.data["driver_license_img_front"]),
                "driver_license_img_back": settings.MEDIA_URL + str(serializer.data["driver_license_img_back"]),
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)


class DriverIdConfirmationViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverIdConfirmationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "put", "patch", "delete", "options"]
    lookup_field = "user_id"

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = []
        for driver in serializer.data:
            idConfirmation = driver["idConfirmation"]
            data.append(
                {
                    "user_id": driver["user_id"],
                    "idConfirmation": settings.MEDIA_URL + str(idConfirmation) if idConfirmation else "",
                }
            )
        return Response({"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def driver_id_confirmation_img(self, request, user_id=None):
        try:
            driver = self.get_object()
            idConfirmation_url = ""
            try:
                idConfirmation_url = str(driver.idConfirmation.url)
            except ValueError:
                pass
            data = {"user_id": driver.user_id, "idConfirmation": idConfirmation_url}
            return Response(
                {"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK
            )
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": "Details not found",
                },
                status=status.HTTP_400_BAD_REQUEST,
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

    @action(detail=True, methods=["put"])
    def update_idConfirm(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            response_data = {
                "status": "OK",
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "user_id": serializer.data["user_id"],
                    "idConfirmation": settings.MEDIA_URL + str(serializer.data["idConfirmation"]),
                },
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": "Details not found",
                },
                status=status.HTTP_400_BAD_REQUEST,
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


class UserDriverDetailsViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = UserDriverDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "options"]
    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            drivers = []
            for driver in queryset:
                user = driver.user
                driver_data = {
                    "user_id": user.id,
                    "email": user.email,
                    "fullname": user.fullname,
                    "phone_no": user.phone_no,
                    "birthdate": user.birthdate if user.birthdate else "",
                    "gender": user.gender,
                    "nationality": user.nationality if user.nationality else "",
                    "profile_img": user.get_profile_img_url(),
                }
                drivers.append(driver_data)
            return Response(drivers)
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

    def retrieve(self, request, *args, **kwargs):
        try:
            driver = self.get_object()
            user = driver.user
            response = {
                "user_id": user.id,
                "email": user.email,
                "fullname": user.fullname,
                "dialCode": user.dialCode if user.dialCode else "",
                "phone_no": user.phone_no,
                "birthdate": user.birthdate if user.birthdate else "",
                "gender": user.gender,
                "nationality": user.nationality if user.nationality else "",
                "profile_img": user.get_profile_img_url(),
            }
            return Response(response)
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
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

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            response_data = {
                "user_id": str(instance.user.id),
                "email": instance.user.email,
                "fullname": instance.user.fullname,
                "dialCode": instance.user.dialCode,
                "phone_no": instance.user.phone_no,
                "birthdate": instance.user.birthdate if instance.user.birthdate else "",
                "gender": instance.user.gender,
                "nationality": instance.user.nationality if instance.user.nationality else "",
                "profile_img": instance.user.profile_img.url if instance.user.profile_img else None,
            }
            return Response(response_data)
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
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

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise exceptions.APIException("Failed to update driver")


class UserSubmissionForm(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = UserDriverDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get"]
    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def retrieve(self, request, *args, **kwargs):
        try:
            driver = self.get_object()
            user = driver.user
            data = {}

            basicinfo = {
                "user_id": user.id,
                "email": user.email,
                "fullname": user.fullname,
                "dialCode": user.dialCode,
                "phone_no": user.phone_no,
                "birthdate": user.birthdate if user.birthdate else "",
                "gender": user.gender if user.gender else "",
                "nationality": user.nationality if user.nationality else "",
                "profile_img": user.get_profile_img_url() if user.get_profile_img_url() else "",
                "isFilled": True
                if user.id and user.email and user.fullname and user.birthdate and user.get_profile_img_url()
                else False,
            }

            try:
                front = driver.driver_license_img_front.url
            except:
                front = None
            try:
                behind = driver.driver_license_img_back.url
            except:
                behind = None

            driver_license = {
                "driver_license_expiry_date": driver.driver_license_expiry_date
                if driver.driver_license_expiry_date
                else "",
                "driver_license_img_front": str(front) if front else "",
                "driver_license_img_back": str(behind) if behind else "",
                "isFilled": True if front and behind and driver.driver_license_expiry_date else False,
            }
            try:
                idConfirmation = driver.idConfirmation.url
            except:
                idConfirmation = None

            license_confirmation = {
                "idConfirmation": str(idConfirmation) if idConfirmation else "",
                "isFilled": True if idConfirmation else False,
            }
            try:
                roadtax = driver.roadtax.url
            except:
                roadtax = None
            vehicleinfo = {
                "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                "vehicle_ownership": driver.vehicle_ownership if driver.vehicle_ownership else "",
                "vehicle_registration_number": driver.vehicle_registration_number
                if driver.vehicle_registration_number
                else "",
                "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
                "roadtax": str(roadtax) if roadtax else "",
                "isFilled": True
                if driver.vehicle_manufacturer
                and driver.vehicle_model
                and driver.vehicle_color
                and driver.vehicle_ownership
                and driver.vehicle_registration_number
                and driver.vehicle_type
                and roadtax
                else False,
            }
            data["basicinfo"] = basicinfo
            data["driver_license"] = driver_license
            data["license_confirmation"] = license_confirmation
            data["vehicleinfo"] = vehicleinfo
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "Driver Application Form Data",
                    "data": data,
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


class DriverVehicleInfoViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverVehicleInfo
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "options"]
    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            drivers = []
            for driver in queryset:
                driver_data = {
                    "user_id": driver.user_id if driver.user_id else "",
                    "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                    "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                    "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                    "vehicle_ownership": driver.vehicle_ownership if driver.vehicle_ownership else "",
                    "vehicle_registration_number": driver.vehicle_registration_number
                    if driver.vehicle_registration_number
                    else "",
                    "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
                    "roadtax": driver.roadtax if driver.roadtax else "",
                }
                drivers.append(driver_data)
            return Response(drivers)
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

    def retrieve(self, request, *args, **kwargs):
        try:
            driver = self.get_object()
            user = driver.user

            try:
                roadtax = driver.roadtax.url
            except:
                roadtax = None

            response = {
                "user_id": user.id,
                "vehicle_manufacturer": driver.vehicle_manufacturer if driver.vehicle_manufacturer else "",
                "vehicle_model": driver.vehicle_model if driver.vehicle_model else "",
                "vehicle_color": driver.vehicle_color if driver.vehicle_color else "",
                "vehicle_ownership": driver.vehicle_ownership if driver.vehicle_ownership else "",
                "vehicle_registration_number": driver.vehicle_registration_number
                if driver.vehicle_registration_number
                else "",
                "vehicle_type": driver.vehicle_type if driver.vehicle_type else "",
                "roadtax": roadtax if roadtax else "",
            }
            return Response(response)
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
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

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            try:
                roadtax = instance.roadtax.url
            except:
                roadtax = None
            response_data = {
                "user_id": str(instance.user.id),
                "vehicle_manufacturer": instance.vehicle_manufacturer if instance.vehicle_manufacturer else "",
                "vehicle_model": instance.vehicle_model if instance.vehicle_model else "",
                "vehicle_color": instance.vehicle_color if instance.vehicle_color else "",
                "vehicle_ownership": instance.vehicle_ownership if instance.vehicle_ownership else "",
                "vehicle_registration_number": instance.vehicle_registration_number
                if instance.vehicle_registration_number
                else "",
                "vehicle_type": instance.vehicle_type if instance.vehicle_type else "",
                "roadtax": roadtax if roadtax else "",
            }
            return Response(response_data)
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
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

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise exceptions.APIException("Failed to update driver")


class DriverStatusViewset(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "options"]

    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def retrieve(self, request, *args, **kwargs):
        try:
            driver = self.get_object()
            user = driver.user

            response_data = {
                "user_id": user.id,
                "statusDriver": driver.statusDriver,
                "message": driver.statusMessage if driver.statusMessage else "",
            }
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "Driver Application Status",
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            response_data = {
                "user_id": str(instance.user.id),
                "statusDriver": instance.statusDriver,
                "message": instance.statusMessage if instance.statusMessage else "",
            }
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "Driver Application Status",
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )

        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
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

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise exceptions.APIException("Failed to update driver")


class DriverJobStatusViewset(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get"]

    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def retrieve(self, request, *args, **kwargs):
        try:
            driver = self.get_object()
            user = driver.user

            response_data = {
                "user_id": user.id,
                "driverJobStatus": driver.jobDriverStatus if driver.jobDriverStatus else "",
            }
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "Driver Job Status",
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Driver not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class PassengerStatusView(viewsets.ModelViewSet):
    queryset = Passenger.objects.all()
    serializer_class = PassengerStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get"]

    lookup_field = "user_id"

    metadata_class = CustomMetadata

    def retrieve(self, request, *args, **kwargs):
        try:
            passenger = self.get_object()
            user = passenger.user

            response_data = {
                "user_id": user.id,
                "passenger_status": passenger.passenger_status if passenger.passenger_status else "",
            }
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "Passenger Status",
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )
        except Http404:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_404_NOT_FOUND,
                    "error": "Not Found",
                    "message": "Passenger not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
