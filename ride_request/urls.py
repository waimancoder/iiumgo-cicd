from django.urls import path
from . import views

urlpatterns = [
    # ... other URL patterns ...
    path(
        "api/ride_request_history/<uuid:user_id>", views.RideRequestHistoryView.as_view(), name="ride_request_history"
    ),
    path(
        "api/driver_ride_request_history/<uuid:user_id>",
        views.DriverRideRequestHistoryView.as_view(),
        name="driver_ride_request_history",
    ),
    path("api/get_price", views.FareEstimationView.as_view(), name="get_price"),
    path("api/get_popular_locations", views.PopularLocationView.as_view(), name="get_popular_locations"),
    path("api/get_cancel_rate", views.DriverCancelRate.as_view(), name="driver_cancel_rate"),
    path("api/rating/<uuid:ride_request_id>", views.RatingAPI.as_view(), name="rating"),
]
