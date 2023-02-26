# Generated by Django 4.1.6 on 2023-02-26 14:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('rides', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='passengers',
            field=models.ManyToManyField(blank=True, related_name='rides', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ride',
            name='passenger',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ride',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rides.trip'),
        ),
        migrations.AddField(
            model_name='driver',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
