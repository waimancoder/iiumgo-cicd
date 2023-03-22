from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import RideRequest
from .serializers import RideRequestSerializer

# Create your views here.


class RideRequestHistoryView(generics.ListAPIView):
    serializer_class = RideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        return RideRequest.objects.filter(user_id=user_id, status=RideRequest.STATUS_COMPLETED)

    def list(self, request, *args, **kwargs):
        try:
            user_id = self.kwargs["user_id"]
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "user_id": user_id,
                    "history": serializer.data,
                },
            }
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": "Please Contact Server Admin",
                    "traceback": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
