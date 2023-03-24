from rest_framework import serializers
from .models import RideRequest


class RideRequestSerializer(serializers.ModelSerializer):
    pickup_time = serializers.SerializerMethodField()
    dropoff_time = serializers.SerializerMethodField()
    actual_fare = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = RideRequest
        fields = (
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_address",
            "dropoff_address",
            "pickup_time",
            "dropoff_time",
            "actual_fare",
            "rating",
            "payment_method",
        )

    def get_pickup_time(self, obj):
        return obj.pickup_time if obj.pickup_time else ""

    def get_dropoff_time(self, obj):
        return obj.dropoff_time if obj.dropoff_time else ""

    def get_actual_fare(self, obj):
        return obj.actual_fare if obj.actual_fare else ""

    def get_rating(self, obj):
        return obj.rating if obj.rating else ""

    def get_payment_method(self, obj):
        return obj.payment_method if obj.payment_method else ""