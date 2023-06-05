from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/home", views.frontpage, name="frontpage"),
    path("admin/login", auth_views.LoginView.as_view(template_name="loginpage.html"), name="loginpage"),
]
