# Generated by Django 4.1.7 on 2023-04-10 19:40

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("advertisement", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="advertisement",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, primary_key=True, serialize=False
            ),
        ),
    ]
