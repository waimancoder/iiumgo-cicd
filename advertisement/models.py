import uuid
from django.core.validators import FileExtensionValidator
from django.db import models


# Create your models here.
class Advertisement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    return_url = models.TextField(blank=True, null=True)
    advertiser = models.CharField(max_length=255, blank=True, null=True)
    phone_no = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(
        upload_to="advertisement_images",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )
    rental_time_from = models.DateTimeField(blank=True, null=True)
    rental_time_to = models.DateTimeField(blank=True, null=True)
    is_valid = models.BooleanField(default=False)
