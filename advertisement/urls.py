from django.urls import path, include
from . import views


urlpatterns = [
    path("api/advertisement", views.AdvertisementView.as_view(), name="advertisement"),
    path("api/todo", views.TodoTaskAPI.as_view(), name="todo"),
    path("api/todo/<uuid:id>", views.TodoTaskChangeStatusAPI.as_view(), name="todo-changeStatus"),
]
