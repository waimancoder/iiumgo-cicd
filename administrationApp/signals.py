import asyncio
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from rides.models import Driver
from .consumers import update_driver_count_async

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Driver)
def update_driver_count_on_create(sender, instance, created, **kwargs):
    try:
        if created:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(update_driver_count_async())
    except Exception as e:
        logger.error(e)
