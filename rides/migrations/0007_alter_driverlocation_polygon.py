# Generated by Django 4.1.7 on 2023-04-15 00:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0006_rename_administrativearea_location_locality_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="driverlocation",
            name="polygon",
            field=models.TextField(blank=True, null=True),
        ),
    ]