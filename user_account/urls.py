from django.conf.urls import handler404
from django.urls import path, reverse
from knox import views as knox_views
from . import views
from .views import (
    DeleteUser,
    PasswordResetAPI,
    RegisterAPI,
    LoginAPI,
    RegisterAPIv2,
    UserRetrieveAPIView,
    PasswordResetView,
    PasswordResetConfirmView,
    ProfilePictureView,
    VerifyEmailAPI,
    verify_email_page,
)
from .views import UserUpdateAPI, UserListView
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from rest_framework import routers


User = get_user_model()
router = routers.SimpleRouter(trailing_slash=False)
router.register(r"api/users", UserRetrieveAPIView, basename="users")


urlpatterns = [
    path("api/login", LoginAPI.as_view(), name="login"),
    path("api/logout", knox_views.LogoutView.as_view(), name="logout"),
    path("api/register", RegisterAPI.as_view(), name="register"),
    path("api/v2/register", RegisterAPIv2.as_view(), name="registerv2"),
    # path('api/studentverification', StudentIDVerificationView.as_view(), name='studentverification'),
    path("api/v2/verify-email/<str:id>", VerifyEmailAPI.as_view(), name="verify-email"),
    path("api/verify-email/<str:uidb64>/<str:token>", views.verify_email, name="verify-email"),
    path("api/password_reset", PasswordResetView.as_view(), name="password_reset"),
    path(
        "api/password_reset_confirm/<str:uidb64>/<str:token>",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("api/password_change", PasswordResetAPI.as_view(), name="password_change"),
    path("api/userupdate/<str:email>", UserUpdateAPI.as_view(), name="userupdate"),
    path("api/userlist", UserListView.as_view(), name="userlist"),
    path("api/profile-pic", ProfilePictureView.as_view(), name="profile-pic"),
    path("api/verify-email-page/<str:uidb64>/<str:token>/", verify_email_page, name="verify-email-page"),
    path("api/delete-account", DeleteUser.as_view(), name="delete-account"),
]

urlpatterns += router.urls
