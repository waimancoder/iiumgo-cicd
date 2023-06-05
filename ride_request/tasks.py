from celery import shared_task
from ride_request.models import CancelRateDriver


@shared_task
def reset_warning_rates():
    for driver in CancelRateDriver.objects.all():
        driver.reset_warning_rate()
