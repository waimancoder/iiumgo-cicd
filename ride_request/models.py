from django.core.validators import FileExtensionValidator
from django.db import models
import uuid
from user_account.models import User
from rides.models import Driver


# Create your models here.
class RideRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    route_polygon = models.CharField(max_length=255, null=True, blank=True)
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    pickup_time = models.DateTimeField(blank=True, null=True)
    dropoff_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name="driver_rides")
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    distance = models.FloatField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    special_requests = models.CharField(max_length=1000, null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    vehicle_type = models.CharField(max_length=255, null=True, blank=True, choices=Driver.typeChoices)


class PopularLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    subLocality = models.CharField(max_length=255, blank=True, null=True)
    locality = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(
        upload_to="popular-location/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Passenger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    STATUS_AVAILABLE = "available"
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_WAITING = "waiting"
    STATUS_IN_PROGRESS = "in_progress"

    STATUS_CHOICES = (
        (STATUS_AVAILABLE, "Available"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_WAITING, "Waiting"),
        (STATUS_PENDING, "Pending"),
    )

    passenger_status = models.CharField(max_length=255, null=True, blank=True, choices=STATUS_CHOICES)
