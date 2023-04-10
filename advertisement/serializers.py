from rest_framework import serializers

from advertisement.models import Advertisement


class AdvertisementSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=100)
    details = serializers.CharField(max_length=1000)
    image = serializers.CharField(max_length=1000)
    return_url = serializers.CharField(max_length=1000)
    advertiser = serializers.CharField(max_length=100)
    phone_no = serializers.CharField(max_length=100)
    rental_time_from = serializers.DateTimeField()
    rental_time_to = serializers.DateTimeField()
    is_valid = serializers.BooleanField()

    class Meta:
        model = Advertisement
        fields = (
            "id",
            "title",
            "details",
            "image",
            "return_url",
            "advertiser",
            "phone_no",
            "rental_time_from",
            "rental_time_to",
            "is_valid",
        )
