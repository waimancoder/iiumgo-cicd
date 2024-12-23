from pyexpat import model
from django.db import models
import ride_request
from user_account.models import User
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
import uuid


class Driver(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle_manufacturer = models.CharField(max_length=128, null=True, blank=True)
    vehicle_model = models.CharField(max_length=128, null=True, blank=True)
    vehicle_color = models.CharField(max_length=128, null=True, blank=True)
    vehicle_registration_number = models.CharField(max_length=128, null=True, blank=True)
    TYPE_4SEATER = "4pax"
    TYPE_6SEATER = "6pax"

    typeChoices = [(TYPE_4SEATER, "4 Seater"), (TYPE_6SEATER, "6 Seater")]
    vehicle_type = models.CharField(max_length=128, null=True, blank=True, choices=typeChoices)
    driver_license_id = models.CharField(max_length=128, null=True, blank=True)
    driver_license_expiry_date = models.DateField(null=True, blank=True)
    driver_license_img_front = models.ImageField(
        upload_to="driver-license/front",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )
    driver_license_img_back = models.ImageField(
        upload_to="driver-license/back",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )
    idConfirmation = models.ImageField(
        upload_to="driver-id-confirmation",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )
    vehicle_img = models.ImageField(
        upload_to="driver-vehicle-img",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )
    roadtax = models.ImageField(
        upload_to="driver-roadtax", null=True, blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png"])]
    )

    statusChoices = [
        ("submitting", "Submitting"),
        ("pending", "Pending"),
        ("activated", "Activated"),
        ("failed", "Failed"),
        ("verified", "Verified"),
    ]
    statusDriver = models.CharField(max_length=20, blank=True, choices=statusChoices, null=True, default="submitting")
    statusMessage = models.CharField(max_length=128, null=True, blank=True)

    STATUS_AVAILABLE = "available"
    STATUS_UNAVAILABLE = "unavailable"
    STATUS_ENROUTE_PICKUP = "enroute_pickup"
    STATUS_WAITING_PICKUP = "waiting_pickup"
    STATUS_IN_TRANSIT = "in_transit"

    statusJobChoices = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
        ("enroute_pickup", "Heading to Passenger"),
        ("waiting_pickup", "Waiting for Passenger"),
        ("in_transit", "In Transit with Passenger"),
    ]
    jobDriverStatus = models.CharField(choices=statusJobChoices, null=True, blank=True, max_length=50)
    CHOICES = [("owned", "Owned"), ("rented", "Rented")]
    vehicle_ownership = models.CharField(max_length=20, blank=True, choices=CHOICES, null=True)
    ride_request = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    @property
    def average_rating(self):
        if self.ratings.count() > 0:
            total_ratings = sum(rating.rating for rating in self.ratings.all())
            return total_ratings / self.ratings.count()
        return None


class DriverRating(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="ratings")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    passenger = models.UUIDField(null=True, blank=True)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class DriverLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    polygon = models.TextField(blank=True, null=True)


class Trip(models.Model):
    origin = models.CharField(max_length=256, blank=True, null=True)
    destination = models.CharField(max_length=256, blank=True, null=True)
    driver = models.ForeignKey(to=Driver, on_delete=models.CASCADE, related_name="trips", blank=True, null=True)
    passengers = models.ManyToManyField(to=User, blank=True, related_name="rides")
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.driver.username} trip from {self.origin} to {self.destination} [{self.start_time}]"


class Ride(models.Model):
    trip = models.ForeignKey(to=Trip, on_delete=models.CASCADE)
    passenger = models.ForeignKey(to=User, on_delete=models.CASCADE)
    status = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.passenger.username} ride on {self.trip.driver.username} trip [{self.status}]"


class Location(models.Model):
    name = models.CharField(unique=True, max_length=255)
    lat = models.CharField(max_length=255, null=True, blank=True)
    lng = models.CharField(max_length=255, null=True, blank=True)
    keywords = models.CharField(max_length=255, null=True, blank=True)
    subLocality = models.CharField(max_length=255, blank=True, null=True)
    locality = models.CharField(max_length=255, blank=True, null=True)
    polygon = models.TextField(blank=True, null=True)


class Block(models.Model):
    name = models.CharField(max_length=255)
    lat = models.CharField(max_length=255)
    lng = models.CharField(max_length=255)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="blocks")
