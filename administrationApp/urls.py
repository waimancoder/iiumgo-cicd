from django.urls import path
from . import views

urlpatterns = [
    path("admin/home", views.frontpage, name="frontpage"),
    path("admin/login", views.loginpage, name="loginpage"),
]
