from django.urls import path
from . import views

urlpatterns = [
    # ... other URL patterns ...
    path(
        "api/ride_request_history/<uuid:user_id>/", views.RideRequestHistoryView.as_view(), name="ride_request_history"
    ),
]
