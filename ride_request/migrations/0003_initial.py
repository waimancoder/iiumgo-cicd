# Generated by Django 4.2 on 2023-05-14 15:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("rides", "0001_initial"),
        ("ride_request", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="riderequest",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="rating",
            name="driver",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="rides.driver",
            ),
        ),
        migrations.AddField(
            model_name="rating",
            name="passenger",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="rating",
            name="ride_request",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                to="ride_request.riderequest",
            ),
        ),
        migrations.AddField(
            model_name="passenger",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="cancelratedriver",
            name="driver",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, to="rides.driver"
            ),
        ),
    ]
