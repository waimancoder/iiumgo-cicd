import logging
from rest_framework import serializers

from payment.models import DriverEarning
import ride_request
from .models import CancelRateDriver, PopularLocation, Rating, RideRequest
import base64
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class RideRequestSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    pickup_time = serializers.SerializerMethodField()
    dropoff_time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    # driver = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    polyline = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    ## DRIVER INFO
    driver_name = serializers.SerializerMethodField()
    vehicle_registration_number = serializers.SerializerMethodField()
    vehicle_manufacturer = serializers.SerializerMethodField()
    vehicle_model = serializers.SerializerMethodField()
    vehicle_color = serializers.SerializerMethodField()
    vehicle_type = serializers.SerializerMethodField()

    # RATING INFO
    rating_id = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    israted = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()

    # payment_method = serializers.SerializerMethodField()

    class Meta:
        model = RideRequest
        fields = (
            "id",
            "status",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_address",
            "dropoff_address",
            "pickup_time",
            "dropoff_time",
            "polyline",
            "price",
            "distance",
            "created_at",
            # "driver",
            "driver_name",
            "vehicle_registration_number",
            "vehicle_manufacturer",
            "vehicle_model",
            "vehicle_color",
            "vehicle_type",
            "rating",
            "israted",
            "comment",
            "rating_id"
            # "commission_paid",
            # "payment_method",
        )

    def get_id(self, obj):
        return obj.id if obj.id else ""

    def get_status(self, obj):
        return obj.status if obj.status else ""

    def get_pickup_time(self, obj):
        return obj.pickup_time if obj.pickup_time else ""

    def get_dropoff_time(self, obj):
        return obj.dropoff_time if obj.dropoff_time else ""

    def get_actual_fare(self, obj):
        return obj.price if obj.price else ""

    def get_rating(self, obj):
        return obj.rating.rating if obj.rating.rating else None

    def get_israted(self, obj):
        return obj.rating.isRated if obj.rating.isRated else False

    def get_comment(self, obj):
        return obj.rating.comment if obj.rating.comment else ""

    def get_rating_id(self, obj):
        return obj.rating.id if obj.rating.id else ""

    def get_price(self, obj):
        return obj.price if obj.price else ""

    # def get_driver(self, obj):
    #     return obj.driver.user.fullname if obj.driver.user.fullname else ""

    def get_distance(self, obj):
        return obj.distance if obj.distance else ""

    def get_polyline(self, obj):
        return obj.route_polygon if obj.route_polygon else ""

    def get_created_at(self, obj):
        return obj.created_at if obj.created_at else ""

    def get_driver_name(self, obj):
        if obj.driver is not None:
            return obj.driver.user.fullname if obj.driver.user.fullname else ""
        else:
            return ""

    def get_vehicle_registration_number(self, obj):
        if obj.driver is not None:
            return obj.driver.vehicle_registration_number if obj.driver.vehicle_registration_number else ""
        else:
            return ""

    def get_vehicle_manufacturer(self, obj):
        if obj.driver is not None:
            return obj.driver.vehicle_manufacturer if obj.driver.vehicle_manufacturer else ""
        else:
            return ""

    def get_vehicle_model(self, obj):
        if obj.driver is not None:
            return obj.driver.vehicle_model if obj.driver.vehicle_model else ""
        else:
            return ""

    def get_vehicle_color(self, obj):
        if obj.driver is not None:
            return obj.driver.vehicle_color if obj.driver.vehicle_color else ""
        else:
            return ""

    def get_vehicle_type(self, obj):
        if obj.driver is not None:
            return obj.driver.vehicle_type if obj.driver.vehicle_type else ""
        else:
            return ""

    # def get_payment_method(self, obj):
    #     return obj.payment_method if obj.payment_method else ""


class DriverRideRequestSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    pickup_time = serializers.SerializerMethodField()
    dropoff_time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    # rating = serializers.SerializerMethodField()
    # driver = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    polyline = serializers.SerializerMethodField()
    earning = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    # commission_paid = serializers.SerializerMethodField()
    # payment_method = serializers.SerializerMethodField()

    class Meta:
        model = RideRequest
        fields = (
            "id",
            "status",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_address",
            "dropoff_address",
            "pickup_time",
            "dropoff_time",
            "polyline",
            "price",
            # "driver",
            "distance",
            # "rating",
            "earning"
            # "payment_method",
        )

    def get_id(self, obj):
        return obj.id if obj.id else ""

    def get_status(self, obj):
        return obj.status if obj.status else ""

    def get_pickup_time(self, obj):
        return obj.pickup_time if obj.pickup_time else ""

    def get_dropoff_time(self, obj):
        return obj.dropoff_time if obj.dropoff_time else ""

    def get_actual_fare(self, obj):
        return obj.price if obj.price else ""

    # def get_rating(self, obj):
    #     return obj.rating if obj.rating else ""

    def get_price(self, obj):
        return obj.price if obj.price else ""

    # def get_driver(self, obj):
    #     return obj.driver.user.fullname if obj.driver.user.fullname else ""

    def get_distance(self, obj):
        return obj.distance if obj.distance else ""

    def get_polyline(self, obj):
        return obj.route_polygon if obj.route_polygon else ""

    def get_earning(self, obj):
        if obj.status == RideRequest.STATUS_COMPLETED:
            driver_id = obj.driver.user.id
            ride_request = obj.id
            earning = DriverEarning.objects.get(driver_id=driver_id, ride_request_id_id=ride_request)
            return earning.earning_amount if earning.earning_amount else ""
        else:
            return ""

    # def get_commission_paid(self, obj):
    #     return obj.commission_paid if obj.commission_paid else ""

    # def get_payment_method(self, obj):
    #     return obj.payment_method if obj.payment_method else ""


class CoordinateSerializer(serializers.Serializer):
    role = serializers.CharField()
    distance = serializers.FloatField()
    pickup_latitude = serializers.FloatField()
    pickup_longitude = serializers.FloatField()
    dropoff_latitude = serializers.FloatField()
    dropoff_longitude = serializers.FloatField()


class PopularLocationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    address = serializers.CharField(required=False)
    image = serializers.CharField(required=False)
    subLocality = serializers.CharField(required=False)
    locality = serializers.CharField(required=False)

    class Meta:
        model = PopularLocation
        fields = ("name", "latitude", "longitude", "address", "image", "subLocality", "locality")


class DriverCancelRateSerializer(serializers.Serializer):
    cancel_rate = serializers.IntegerField(required=False)
    warning_rate = serializers.IntegerField(required=False)

    class Meta:
        model = CancelRateDriver
        fields = ("cancel_rate", "warning_rate")


class RatingSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    rating = serializers.IntegerField(required=False)
    comment = serializers.CharField(required=False)
    isRated = serializers.BooleanField(required=False)

    class Meta:
        model = Rating
        fields = ("id", "rating", "comment", "isRated")

    def validate(self, attrs):
        rating = attrs.get("rating")
        if rating < 1 or rating > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return attrs
