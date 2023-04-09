from dataclasses import fields
from datetime import datetime
from rest_framework import serializers, status
from django.core.files.base import ContentFile
from rest_framework.authentication import get_user_model
from rest_framework.fields import ChoiceField
from .models import Driver, DriverLocation, Location
import base64
from user_account.models import User
from django.core.files.uploadedfile import UploadedFile


User = get_user_model()


class DateField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if value == "":
            return None
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise serializers.ValidationError("Invalid date format. Date should be in yyyy-mm-dd format.")
        return date_obj

    def to_representation(self, value):
        iso_date_str = value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return iso_date_str


class DriverLicenseSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(read_only=True)
    driver_license_img_front = serializers.CharField(required=False, allow_blank=True)
    driver_license_img_back = serializers.CharField(required=False, allow_blank=True)
    driver_license_expiry_date = DateField(required=False, allow_null=True)

    class Meta:
        model = Driver
        fields = ["user_id", "driver_license_img_front", "driver_license_img_back", "driver_license_expiry_date"]
        read_only_fields = ["user_id"]

    def update(self, instance, validated_data):
        print("Update method called")
        try:
            driver_license_expiry_date = validated_data.get("driver_license_expiry_date")
        except:
            pass
        driver_license_img_front = validated_data.get("driver_license_img_front", None)
        driver_license_img_back = validated_data.get("driver_license_img_back", None)

        if driver_license_img_front:
            # Decode the base64-encoded image data
            format, imgstr = driver_license_img_front.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"{instance.user_id}_driver_license_img_front.{ext}")

            instance.driver_license_img_front = data
            instance.save()

        if driver_license_img_back:
            # Decode the base64-encoded image data
            format, imgstr = driver_license_img_back.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"{instance.user_id}_driver_license_img_back.{ext}")

            instance.driver_license_img_back = data
            instance.save()

        instance.driver_license_expiry_date = driver_license_expiry_date
        instance.save()

        return instance


class DriverIdConfirmationSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(read_only=True)
    idConfirmation = serializers.CharField(allow_blank=True)

    class Meta:
        model = Driver
        fields = ["user_id", "idConfirmation"]
        read_only_fields = ["user_id"]

    def update(self, instance, validated_data):
        print("Update method called")
        idConfirmation = validated_data.get("idConfirmation", None)

        if idConfirmation:
            # Decode the base64-encoded image data
            format, imgstr = idConfirmation.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"{instance.user_id}_idConfirmation.{ext}")

            instance.idConfirmation = data
            instance.save()

        return instance


class UserDriverDetailsSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", required=False)
    fullname = serializers.CharField(source="user.fullname", required=False)
    phone_no = serializers.CharField(source="user.phone_no", required=False)
    birthdate = serializers.DateTimeField(source="user.birthdate", required=False)
    profile_img = serializers.CharField(source="user.profile_img", required=False)
    profile_img_url = serializers.SerializerMethodField()
    gender = serializers.CharField(source="user.gender", required=False)
    nationality = serializers.CharField(source="user.nationality", required=False)
    dialCode = serializers.CharField(source="user.dial_code", required=False)

    def get_profile_img_url(self, instance):
        return instance.user.get_profile_img_url()

    class Meta:
        model = Driver
        fields = (
            "user_id",
            "email",
            "fullname",
            "dialCode",
            "phone_no",
            "birthdate",
            "gender",
            "nationality",
            "profile_img",
            "profile_img_url",
        )
        read_only_fields = ["user_id", "profile_img_url"]

    def update(self, instance, validated_data):
        try:
            # Extract user-related fields from validated_data
            user_data = validated_data.pop("user", {})

            # Update the associated User object's fields
            user = instance.user
            if "email" in user_data:
                email = user_data["email"]
                if email != user.email:
                    if User.objects.filter(email=email).exclude(id=user.id).exists():
                        error_msg = {
                            "success": False,
                            "statusCode": status.HTTP_400_BAD_REQUEST,
                            "error": "Bad Request",
                            "message": "Email already exists",
                        }
                        raise serializers.ValidationError(error_msg)
                    user.email = email
                    user.username = email.split("@")[0]

            user.fullname = user_data.get("fullname", user.fullname)
            user.phone_no = user_data.get("phone_no", user.phone_no)
            user.birthdate = user_data.get("birthdate", user.birthdate)
            user.gender = user_data.get("gender", user.gender)
            user.nationality = user_data.get("nationality", user.nationality)
            user.dialCode = user_data.get("dialCode", user.dialCode)

            if user_data.get("profile_img"):
                profile_img = user_data.get("profile_img")
                format, imgstr = profile_img.split(";base64,")
                ext = format.split("/")[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"{user.username}_profile.{ext}")
                user.profile_img = data

            user.save()

            # Update the Driver object's fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            return instance
        except serializers.ValidationError as e:
            error_msg = {
                "success": False,
                "statusCode": status.HTTP_400_BAD_REQUEST,
                "error": "Bad Request",
                "message": e.detail,
            }
            raise serializers.ValidationError(error_msg)

        except Exception as e:
            print(e)
            error_msg = {
                "success": False,
                "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "Internal Server Error",
                "message": "Failed to update driver",
            }
            raise serializers.ValidationError(error_msg)


class DriverVehicleInfo(serializers.ModelSerializer):
    vehicle_manufacturer = serializers.CharField(required=False, allow_blank=True)
    vehicle_model = serializers.CharField(required=False, allow_blank=True)
    vehicle_color = serializers.CharField(required=False, allow_blank=True)
    vehicle_ownership = serializers.CharField(required=False, allow_blank=True)
    vehicle_registration_number = serializers.CharField(required=False, allow_blank=True)
    vehicle_type = serializers.ChoiceField(choices=[("4pax", "4pax"), ("6pax", "6pax"), ("", "")], required=False)
    roadtax = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Driver
        fields = (
            "vehicle_manufacturer",
            "vehicle_model",
            "vehicle_color",
            "vehicle_ownership",
            "vehicle_registration_number",
            "vehicle_type",
            "roadtax",
        )

    def update(self, instance, validated_data):
        print("Update method called")
        roadtax_file = validated_data.get("roadtax", None)

        if roadtax_file:
            # Decode the base64-encoded image data
            format, imgstr = roadtax_file.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"{instance.user_id}_roadtax.{ext}")

            instance.roadtax = data

        instance.vehicle_color = validated_data.get("vehicle_color", None) or None
        instance.vehicle_ownership = validated_data.get("vehicle_ownership", None) or None
        instance.vehicle_manufacturer = validated_data.get("vehicle_manufacturer", None) or None
        instance.vehicle_model = validated_data.get("vehicle_model", None) or None
        instance.vehicle_registration_number = validated_data.get("vehicle_registration_number", None) or None
        instance.vehicle_type = validated_data.get("vehicle_type", None) or None

        instance.save()

        return instance


class DriverLocationSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = DriverLocation
        fields = ["user_id", "latitude", "longitude"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ("name", "polygon", "lat", "lng")

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.polygon = validated_data.get("polygon", instance.polygon)
        instance.lat = validated_data.get("lat", instance.lat)
        instance.lng = validated_data.get("lng", instance.lng)
        instance.save()

        return instance


class DriverStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ("statusDriver", "statusMessage")


class DriverJobStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "statusJob"
