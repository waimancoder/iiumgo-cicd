from django.urls import path, include
from . import views


urlpatterns = [
    path("api/advertisement", views.AdvertisementView.as_view(), name="advertisement"),
]
