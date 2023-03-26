from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import RideRequest
from .serializers import RideRequestSerializer
from rest_framework.pagination import PageNumberPagination


# Create your views here.
class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"


class RideRequestHistoryView(generics.ListAPIView):
    serializer_class = RideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        return RideRequest.objects.filter(user_id=user_id, status=RideRequest.STATUS_COMPLETED).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        try:
            user_id = self.kwargs["user_id"]
            queryset = self.get_queryset()
            paginated_queryset = self.paginate_queryset(queryset)

            print(paginated_queryset)

            serializer = self.get_serializer(paginated_queryset, many=True)

            response = {
                "status": True,
                "statusCode": status.HTTP_200_OK,
                "data": {
                    "user_id": user_id,
                    "history": serializer.data,
                    "count": queryset.count(),
                    "next": self.paginator.get_next_link(),
                    "previous": self.paginator.get_next_link(),
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
