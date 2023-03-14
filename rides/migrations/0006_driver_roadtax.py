# Generated by Django 4.1.6 on 2023-03-14 11:47

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rides', '0005_alter_driver_statusdriver_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='roadtax',
            field=models.ImageField(blank=True, null=True, upload_to='driver-roadtax', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png'])]),
        ),
    ]
