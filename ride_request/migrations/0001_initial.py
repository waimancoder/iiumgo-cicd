# Generated by Django 4.1.6 on 2023-03-21 03:17

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RideRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('pickup_latitude', models.FloatField()),
                ('pickup_longitude', models.FloatField()),
                ('route_polygon', models.CharField(blank=True, max_length=255, null=True)),
                ('dropoff_latitude', models.FloatField()),
                ('dropoff_longitude', models.FloatField()),
                ('pickup_address', models.CharField(max_length=255)),
                ('dropoff_address', models.CharField(max_length=255)),
                ('pickup_time', models.DateTimeField(blank=True, null=True)),
                ('dropoff_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('canceled', 'Canceled')], default='pending', max_length=20)),
                ('estimated_fare', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('actual_fare', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('payment_method', models.CharField(blank=True, max_length=20, null=True)),
                ('distance', models.FloatField(blank=True, null=True)),
                ('duration', models.IntegerField(blank=True, null=True)),
                ('special_requests', models.TextField(blank=True, null=True)),
                ('rating', models.FloatField(blank=True, null=True)),
            ],
        ),
    ]
