# Generated by Django 4.1.7 on 2023-04-09 19:39

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0004_location_administrativearea_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="location",
            name="polygon",
        ),
    ]