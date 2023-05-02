# Generated by Django 4.2 on 2023-05-02 14:55

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0008_location_polygon"),
        ("ride_request", "0013_riderequest_israted"),
    ]

    operations = [
        migrations.CreateModel(
            name="CancelRateDriver",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("cancel_rate", models.IntegerField(blank=True, default=0, null=True)),
                ("warning_rate", models.IntegerField(blank=True, default=0, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "driver",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="rides.driver"
                    ),
                ),
            ],
        ),
    ]