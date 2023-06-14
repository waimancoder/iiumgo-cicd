import base64
from calendar import c
import traceback
import uuid
from django.http import Http404, JsonResponse
import requests
from rest_framework import generics, permissions, status, serializers, mixins, viewsets
from rest_framework.exceptions import ErrorDetail
from .serializers import (
    PasswordResetInAppSerializer,
    RegisterSerializerV2,
    UserSerializer,
    AuthTokenSerializer,
    RegisterSerializer,
    StudentIDVerificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    ProfilePictureSerializer,
    VerifyEmailSerializer,
)
from rest_framework.response import Response
from knox.models import AuthToken
from rest_framework.permissions import IsAuthenticated
from knox.views import LoginView as KnoxLoginView
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator as auth_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from mytaxi import settings
from rest_framework.decorators import api_view
from .models import User
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import sys
from django.core.mail import EmailMessage
from .models import StudentID
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from mytaxi.scheme import KnoxTokenScheme
from pyotp import TOTP


import logging

logger = logging.getLogger(__name__)


User = get_user_model()


def custom_500_page_not_found(request):
    tb = traceback.format_exc().splitlines()[-5:]
    error_msg = f"Internal Server Error: {tb}"
    return JsonResponse(
        {
            "success": False,
            "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error": "Internal Server Error, Please Contact Server Admin",
            "exception": str(sys.exc_info()[1]),
            "traceback": error_msg,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def custom_404_page_not_found(request, exception):
    if request.META.get("HTTP_ACCEPT", "").startswith("text/html"):
        return render(request, "400.html")
    else:
        return JsonResponse(
            {
                "success": False,
                "statusCode": status.HTTP_404_NOT_FOUND,
                "error": "Page Not Found or Invalid API Endpoint",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


# Create your views here.
class UserRetrieveAPIView(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "options"]
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        data = serializer.data
        for key, value in data.items():
            if value is None:
                data[key] = ""

        return Response(
            {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except serializers.ValidationError as e:
            errors = e.detail
            message = str(errors[list(errors.keys())[0]][0])
            message = "Email already exists." if message == "This field must be unique." else message
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": message,
                    "line": sys.exc_info()[-1].tb_lineno,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_site = get_current_site(request)
        subject = "Verify your email address"
        message = render_to_string(
            "verification_email.html",
            {
                "user": user,
                "fullname": user.fullname,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": auth_token_generator.make_token(user),
            },
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=message,
        )
        user_data = UserSerializer(user, context=self.get_serializer_context()).data

        userinfo = {
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "fullname": user_data.get("fullname"),
            "dialCode": user_data.get("dialCode"),
            "phone_no": user_data.get("phone_no"),
            "role": user_data.get("role"),
            "isVerified": user_data.get("isVerified"),
            # "birthdate": user_data.get("birthdate") if user_data.get("birthdate") else "",
            "gender": user_data.get("gender") if user_data.get("gender") else "",
            # "nationality": user_data.get("nationality") if user_data.get("nationality") else "",
        }

        # if user_data.get("role") == "student":
        #     userinfo["matricNo"] = user_data.get("matricNo")
        #     userinfo["student_pic"] = user_data.get("student_pic")

        return Response({"user": userinfo, "token": AuthToken.objects.create(user)[1]})

    def options(self, request, *args, **kwargs):
        methods = ["POST", "OPTIONS"]
        content_types = ["application/json"]
        headers = {
            "Allow": ", ".join(methods),
            "Content-Type": ", ".join(content_types),
        }
        return Response(
            {"methods": methods, "content_types": content_types, "headers": headers},
            status=status.HTTP_200_OK,
            headers=headers,
        )


class LoginAPI(KnoxLoginView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AuthTokenSerializer

    def post(self, request, format=None):
        try:
            serializer = self.serializer_class(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            username = serializer.validated_data["username"]
            user = User.objects.get(username=username)  # get User instance
            token_ttl = self.get_token_ttl()
            instance, token = AuthToken.objects.create(user, token_ttl)  # pass User instance to create()
            user_logged_in.send(sender=user.__class__, request=request, user=user)
            data = self.get_post_response_data(request, token, instance)

            basicinfo = {
                "id": user.id,
                "email": user.email,
                "fullname": user.fullname,
                "dialCode": user.dialCode if user.dialCode else "",
                "phone_no": user.phone_no if user.phone_no else "",
                "role": user.role,
                "birthdate": user.birthdate if user.birthdate else "",
                "gender": user.gender if user.gender else "",
                "nationality": user.nationality if user.nationality else "",
                "profile_img": user.get_profile_img_url(),
                "isVerified": user.isVerified,
                "expiry": data.get("expiry"),
                "token": data.get("token"),
            }

            response_data = {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "data": basicinfo,
            }

            return Response(response_data)
        except serializers.ValidationError as error:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_401_UNAUTHORIZED,
                    "error": "Invalid Email or Password",
                    "message": error.detail.get("non_field_errors", "Invalid email or password"),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

    #         # TODO: bila ada email company nanti uncomment
    # if user.isVerified is False:
    #     return Response({
    #     "success": False,
    #     "statusCode": status.HTTP_400_BAD_REQUEST,
    #     "error": "Bad Request",
    #     "message": "User is not verified",
    #      }, status=status.HTTP_400_BAD_REQUEST)
    # else:
    #     login(request, user)
    #     response_data = {'id': user.id, 'email': user.email}
    #     response_data.update(super().post(request, format=None).data)


@api_view(["GET"])
def verify_email(request, uidb64, token):
    User = get_user_model()

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and auth_token_generator.check_token(user, token):
        user.isVerified = True
        user.save()
        return Response(
            {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "message": "Your email address has been verified.",
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {
                "success": False,
                "statusCode": status.HTTP_400_BAD_REQUEST,
                "error": "Bad Request",
                "message": "Verification link is invalid!",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                try:
                    user = User.objects.get(email=serializer.data["email"])
                    send_password_reset_email(request, user)
                    return Response(
                        {
                            "success": True,
                            "statusCode": status.HTTP_200_OK,
                            "message": "Password reset email sent",
                        }
                    )
                except User.DoesNotExist:
                    return Response(
                        {
                            "success": False,
                            "statusCode": status.HTTP_400_BAD_REQUEST,
                            "error": "Bad Request",
                            "message": "User not found",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                    {
                        "success": False,
                        "statusCode": status.HTTP_400_BAD_REQUEST,
                        "error": "Bad Request",
                        "message": "Invalid request data",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": "Internal Server Error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def send_password_reset_email(request, user):
    current_site = get_current_site(request)
    subject = "Do Not Reply: Password reset request"
    message = render_to_string(
        "password_reset_email.html",
        {
            "user": user,
            "domain": current_site.domain,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": auth_token_generator.make_token(user),
        },
    )
    to_email = user.email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        html_message=message,
    )


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            print(serializer.data)
            if "new_password1" not in request.data:
                return Response(
                    {
                        "success": False,
                        "statusCode": status.HTTP_400_BAD_REQUEST,
                        "error": "Bad Request",
                        "message": "new_password1 field is missing from the request payload",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                uid = force_str(urlsafe_base64_decode(serializer.data["uid"]))
                user = User.objects.get(pk=uid)
                user.set_password(serializer.data["new_password1"])
                user.full_clean()
                user.save()
                update_session_auth_hash(request, user)
                token = AuthToken.objects.create(user)[1]
                return Response({"token": token})
            except ValidationError as e:
                return Response({"error": e})
        else:
            print(serializer.errors)  # add this line
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserUpdateAPI(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "email"
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        return Response(data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        user = self.get_object()
        # if user.role == 'student':
        #     student_id = StudentID.objects.get(user=user)
        #     student_id_serializer = StudentIDVerificationSerializer(student_id, data=request.data)
        #     if student_id_serializer.is_valid():
        #         student_id_serializer.save()
        user_serializer = UserSerializer(user, data=request.data)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "User details updated",
                    "data": UserSerializer(user).data,
                }
            )
        return Response(
            {
                "success": False,
                "statusCode": status.HTTP_400_BAD_REQUEST,
                "error": "Bad Request",
                "message": user_serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        try:
            users = self.get_queryset()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class ProfilePictureView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfilePictureSerializer

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        user = self.request.user

        if user.profile_img:
            profile_img = settings.MEDIA_URL + str(user.profile_img)
        else:
            profile_img = None

        return Response({"profile_img": profile_img})

    def put(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return self.get(request, *args, **kwargs)


def verify_email_page(request, uidb64, token):
    context = {
        "uidb64": uidb64,
        "token": token,
    }

    return render(request, "verification.html", context)


class PasswordResetAPI(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordResetInAppSerializer

    def post(self, request, *args, **kwargs):
        try:
            user = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if not user.check_password(serializer.data["current_password"]):
                return Response(
                    {
                        "success": False,
                        "statusCode": status.HTTP_400_BAD_REQUEST,
                        "error": "Bad Request",
                        "message": "Current password is incorrect",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info("Password reset request for user: " + str(user))
            user.set_password(serializer.data["new_password"])
            user.save()

            return Response(
                {
                    "success": True,
                    "statusCode": status.HTTP_200_OK,
                    "message": "Password changed successfully",
                },
                status=status.HTTP_200_OK,
            )
        except serializers.ValidationError as e:
            error_detail = e.detail.get("non_field_errors", [])[0]
            error_message = error_detail.__str__()

            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": error_message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class RegisterAPIv2(generics.GenericAPIView):
    serializer_class = RegisterSerializerV2

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except serializers.ValidationError as e:
            errors = e.detail
            message = str(errors[list(errors.keys())[0]][0])
            message = "Email already exists." if message == "This field must be unique." else message
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": message,
                    "line": sys.exc_info()[-1].tb_lineno,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_site = get_current_site(request)
        subject = "Verify your email address"
        message = render_to_string(
            "verification_emailv2.html",
            {
                "user": user,
                "fullname": user.fullname,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": auth_token_generator.make_token(user),
                "otp": otp,
            },
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=message,
        )
        user_data = UserSerializer(user, context=self.get_serializer_context()).data
        user_object = User.objects.get(id=user_data.get("id"))
        # GENERATE OTP
        base32secret = uuid_to_base32(user_object)
        logger.critical("BASE32SECRET: " + str(base32secret))
        totp = TOTP(base32secret)
        totp.interval = 120
        otp = totp.now()
        logger.critical("OTP: " + str(otp))

        userinfo = {
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "fullname": user_data.get("fullname"),
            "dialCode": user_data.get("dialCode"),
            "phone_no": user_data.get("phone_no"),
            "role": user_data.get("role"),
            "isVerified": user_data.get("isVerified"),
            # "birthdate": user_data.get("birthdate") if user_data.get("birthdate") else "",
            "gender": user_data.get("gender") if user_data.get("gender") else "",
            # "nationality": user_data.get("nationality") if user_data.get("nationality") else "",
        }

        # if user_data.get("role") == "student":
        #     userinfo["matricNo"] = user_data.get("matricNo")
        #     userinfo["student_pic"] = user_data.get("student_pic")

        return Response({"user": userinfo, "token": AuthToken.objects.create(user)[1]})

    def options(self, request, *args, **kwargs):
        methods = ["POST", "OPTIONS"]
        content_types = ["application/json"]
        headers = {
            "Allow": ", ".join(methods),
            "Content-Type": ", ".join(content_types),
        }
        return Response(
            {"methods": methods, "content_types": content_types, "headers": headers},
            status=status.HTTP_200_OK,
            headers=headers,
        )


class VerifyEmailAPI(generics.GenericAPIView):
    """
    Verify Email API
    Description: Verify email using OTP
    """

    serializer_class = VerifyEmailSerializer
    http_method_names = ["post"]
    lookup_field = "id"

    def post(self, request, id, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = User.objects.get(id=id)
            base32secret = uuid_to_base32(user)
            logger.critical("BASE32SECRET: " + str(base32secret))
            totp = TOTP(base32secret)
            totp.interval = 120

            if totp.verify(serializer.data["otp"]):
                user.isVerified = True
                user.save()
                return Response(
                    {
                        "success": True,
                        "statusCode": status.HTTP_200_OK,
                        "message": "Email verified successfully",
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "statusCode": status.HTTP_400_BAD_REQUEST,
                        "error": "Bad Request",
                        "message": "Invalid OTP",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "error": "Bad Request",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# GENERATE BASE32 SECRET
def uuid_to_base32(user):
    uuid_bytes = user.id.bytes
    base32_bytes = base64.b32encode(uuid_bytes).rstrip(b"=").decode("ascii")
    return base32_bytes
