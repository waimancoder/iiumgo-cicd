from django.contrib.auth import tokens
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from ride_request.models import RideRequest
from user_account.models import User
from knox.models import AuthToken


class RideRequestHistoryViewTestCase(APITestCase):
    def setUp(self):
        # Create a test user and authenticate
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        token = AuthToken.objects.create(self.user)[1]
        self.client = APIClient()
        self.client.login(username=self.username, password=self.password)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

        # Create some test ride requests for the user
        self.ride_request1 = RideRequest.objects.create(
            user=self.user,
            pickup_latitude="37.7749",
            pickup_longitude="-122.4194",
            dropoff_latitude="37.7934",
            dropoff_longitude="-122.4088",
            pickup_address="123 Main St, San Francisco, CA",
            dropoff_address="456 Elm St, San Francisco, CA",
            route_polygon="ABCDEF",
            price=10.00,
            distance=2.5,
            status=RideRequest.STATUS_CANCELED,
        )
        self.ride_request2 = RideRequest.objects.create(
            user=self.user,
            pickup_latitude="37.7749",
            pickup_longitude="-122.4194",
            dropoff_latitude="37.7934",
            dropoff_longitude="-122.4088",
            pickup_address="123 Main St, San Francisco, CA",
            dropoff_address="456 Elm St, San Francisco, CA",
            route_polygon="ABCDEF",
            price=10.00,
            distance=2.5,
            status=RideRequest.STATUS_COMPLETED,
        )

    def test_list_ride_requests(self):
        url = reverse("ride_request_history", kwargs={"user_id": self.user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], True)
        self.assertEqual(response.data["data"]["user_id"], self.user.id)
        self.assertEqual(len(response.data["data"]["history"]), 2)
        self.assertEqual(response.data["data"]["history"][0]["id"], self.ride_request2.id)
        self.assertEqual(response.data["data"]["history"][0]["status"], RideRequest.STATUS_COMPLETED)
        self.assertEqual(response.data["data"]["history"][0]["pickup_latitude"], 37.7749)
        self.assertEqual(response.data["data"]["history"][0]["pickup_longitude"], -122.4194)
        self.assertEqual(response.data["data"]["history"][0]["dropoff_latitude"], 37.7934)
        self.assertEqual(response.data["data"]["history"][0]["dropoff_longitude"], -122.4088)
        self.assertEqual(response.data["data"]["history"][0]["pickup_address"], "123 Main St, San Francisco, CA")
        self.assertEqual(response.data["data"]["history"][0]["dropoff_address"], "456 Elm St, San Francisco, CA")
        self.assertEqual(response.data["data"]["history"][0]["polyline"], "ABCDEF")
        self.assertEqual(response.data["data"]["history"][0]["price"], 10.00)
        self.assertEqual(response.data["data"]["history"][0]["distance"], 2.5)
        self.assertEqual(response.data["data"]["history"][1]["id"], self.ride_request1.id)
        self.assertEqual(response.data["data"]["history"][1]["status"], RideRequest.STATUS_CANCELED)
        self.assertEqual(response.data["data"]["history"][1]["pickup_latitude"], 37.7749)
        self.assertEqual(response.data["data"]["history"][1]["pickup_longitude"], -122.4194)
        self.assertEqual(response.data["data"]["history"][1]["dropoff_latitude"], 37.7934)
        self.assertEqual(response.data["data"]["history"][1]["dropoff_longitude"], -122.4088)
        self.assertEqual(response.data["data"]["history"][1]["pickup_address"], "123 Main St, San Francisco, CA")
        self.assertEqual(response.data["data"]["history"][1]["dropoff_address"], "456 Elm St, San Francisco, CA")
        self.assertEqual(response.data["data"]["history"][1]["polyline"], "ABCDEF")
        self.assertEqual(response.data["data"]["history"][1]["price"], 10.00)
        self.assertEqual(response.data["data"]["history"][1]["distance"], 2.5)

    def tearDown(self):
        # Logout and delete test user and ride requests
        self.client.logout()
        self.user.delete()
        self.ride_request1.delete()
        self.ride_request2.delete()
