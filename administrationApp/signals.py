import asyncio
from django.db.models.signals import post_save
from django.dispatch import receiver
from rides.models import Driver
from .consumers import update_driver_count_async


@receiver(post_save, sender=Driver)
def update_driver_count_on_create(sender, instance, created, **kwargs):
    print("Driver created")
    if created:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(update_driver_count_async())
