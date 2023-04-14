import base64
import random
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers

from advertisement.models import Advertisement


class AdvertisementSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=100)
    details = serializers.CharField(max_length=1000, required=False)
    image = serializers.CharField(required=False)
    return_url = serializers.CharField(max_length=1000, required=False)
    advertiser = serializers.CharField(max_length=100, required=False)
    phone_no = serializers.CharField(max_length=100, required=False)
    rental_time_from = serializers.DateTimeField(required=False)
    rental_time_to = serializers.DateTimeField(required=False)
    is_valid = serializers.BooleanField(required=False)

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

    def create(self, validated_data):
        advertisement = Advertisement.objects.create(
            title=validated_data["title"],
            details=validated_data["details"],
            return_url=validated_data["return_url"],
            advertiser=validated_data["advertiser"],
            phone_no=validated_data["phone_no"],
            rental_time_from=validated_data["rental_time_from"],
            rental_time_to=validated_data["rental_time_to"],
            is_valid=validated_data["is_valid"],
        )
        image = validated_data.pop("image", None)
        if image:
            # Decode the base64 string into binary image data
            random_number = random.randint(0, 100)
            format, imgstr = image.split(";base64,")
            ext = format.split("/")[-1]
            image_data = ContentFile(base64.b64decode(imgstr), name=f"advertisement_{random_number}.{ext}")
            advertisement.image = image_data
        advertisement.save()

        return advertisement
