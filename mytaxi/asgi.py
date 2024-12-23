"""
ASGI config for mytaxi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mytaxi.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path, path
import mytaxi.consumers as mytaxi_consumers
import ride_request.consumers as riderequest_consumers
import administrationApp.consumers as admin_consumers

websocket_urlpatterns = [
    re_path(r"ws/dummy/$", mytaxi_consumers.DummyConsumer.as_asgi()),
    re_path(r"ws/driver/(?P<user_id>[^/]+)$", riderequest_consumers.DriverConsumer.as_asgi()),
    re_path(r"ws/passenger/(?P<user_id>[^/]+)$", riderequest_consumers.PassengerConsumer.as_asgi()),
    re_path(r"ws/location/(?P<user_id>[^/]+)$", riderequest_consumers.LocationConsumer.as_asgi()),
    re_path(r"ws/driver_count/$", admin_consumers.DriverCountConsumer.as_asgi()),
]


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
