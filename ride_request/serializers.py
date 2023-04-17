from rest_framework import serializers

from payment.models import DriverEarning
import ride_request
from .models import PopularLocation, RideRequest
import base64
from django.core.files.base import ContentFile


class RideRequestSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    pickup_time = serializers.SerializerMethodField()
    dropoff_time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    # rating = serializers.SerializerMethodField()
    # driver = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    polyline = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
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
