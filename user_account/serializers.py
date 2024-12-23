from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model, authenticate, update_session_auth_hash
from django.utils.translation import gettext_lazy as _
from payment.models import DriverEwallet

from ride_request.models import Passenger
from .models import User, StudentID
from django.shortcuts import get_list_or_404, get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator as auth_token_generator
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
import base64
from django.core.files.base import ContentFile
from rides.models import Driver, DriverLocation
from datetime import datetime
import secrets


User = get_user_model()


class DateField(serializers.DateTimeField):
    def to_internal_value(self, value):
        try:
            date_obj = datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            raise serializers.ValidationError("Invalid date format. Date should be in dd/mm/yyyy format.")

        cleaned_date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().to_internal_value(cleaned_date_str)


class UserSerializer(serializers.ModelSerializer):
    matricNo = serializers.SerializerMethodField()
    birthdate = DateField()
    student_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "fullname",
            "dialCode",
            "phone_no",
            "role",
            "isVerified",
            "birthdate",
            "gender",
            "nationality",
            "matricNo",
            "student_pic",
        ]
        read_only_fields = ["isVerified", "role"]

    def get_matricNo(self, instance):
        try:
            student_id = StudentID.objects.get(user=instance)
            matric_no = student_id.matricNo
            return matric_no
        except StudentID.DoesNotExist:
            matric_no = None

    def get_student_pic(self, instance):
        try:
            student_id = StudentID.objects.get(user=instance)
            student_pic = student_id.student_pic.url
            return student_pic
        except StudentID.DoesNotExist:
            student_pic = None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["role"] != "student":
            data.pop("matricNo")
            data.pop("student_pic")
        return data

    def update(self, instance, validated_data):
        studentID_data = validated_data.pop("StudentID", {})
        StudentID = instance.StudentID
        if "matricNo" in studentID_data and StudentID.matricNo is None:
            StudentID.matricNo = studentID_data["matricNo"]
            StudentID.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=get_user_model().objects.all())])
    fullname = serializers.CharField(max_length=100)
    phone_no = serializers.CharField(max_length=12)
    # matricNo = serializers.CharField(max_length=12, required=False)
    # student_pic = serializers.CharField(required=False)
    gender = serializers.CharField(max_length=10, required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "fullname",
            "password",
            "phone_no",
            "dialCode",
            "role",
            "gender",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def create_unique_username(self, local_part):
        while True:
            random_str = secrets.token_hex(3)
            username = f"{local_part}_{random_str}"
            if not User.objects.filter(username=username).exists():
                return username

    def create(self, validated_data):
        try:
            email = validated_data["email"]
            local_part = email.split("@")[0]

            username = self.create_unique_username(local_part)

            user = User.objects.create_user(username, validated_data["email"], validated_data["password"])
            user.fullname = validated_data["fullname"]
            user.phone_no = validated_data["phone_no"]
            user.dialCode = validated_data["dialCode"]
            user.role = validated_data["role"]
            user.gender = validated_data["gender"]

            user.save()

            if user.role == "student":
                Driver.objects.create(
                    user=user,
                    vehicle_manufacturer="",
                    vehicle_model="",
                    vehicle_color="",
                    vehicle_ownership="",
                    vehicle_registration_number="",
                    driver_license_id="",
                    driver_license_img_front=None,
                    driver_license_img_back=None,
                    idConfirmation=None,
                    vehicle_img=None,
                    statusDriver="submitting",
                    statusMessage="submitting",
                )
                DriverLocation.objects.create(
                    user=user,
                    latitude=None,
                    longitude=None,
                )
                # if validated_data["matricNo"] and validated_data["student_pic"]:
                #     student_pic = validated_data["student_pic"]
                #     format, imgstr = student_pic.split(";base64,")
                #     ext = format.split("/")[-1]
                #     data = ContentFile(base64.b64decode(imgstr), name=f"{user.username}_student_pic.{ext}")
                #     matricNo = validated_data["matricNo"]
                #     StudentID.objects.create(
                #         user=user,
                #         matricNo=matricNo,
                #         student_pic=data,
                #     )

            DriverEwallet.objects.create(user=user)
            Passenger.objects.create(user=user, passenger_status=Passenger.STATUS_AVAILABLE)

            return user
        except Exception as e:
            print(e)
            raise e


class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(request=self.context.get("request"), username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password")

        attrs["username"] = user.username
        return attrs


class StudentIDVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentID
        fields = ["matricNo"]


class VerifyEmailSerializer(serializers.Serializer):
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetInAppSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        current_password = attrs.get("current_password")
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        if current_password == new_password:
            raise serializers.ValidationError("New password cannot be the same as the old password")

        if new_password != confirm_password:
            raise serializers.ValidationError("New password and confirm password must be the same")

        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password1 = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError({"error": "User not found"})

        if not auth_token_generator.check_token(user, data["token"]):
            raise ValidationError({"error": "Invalid token"})

        password_reset_form = SetPasswordForm(user, data)
        if not password_reset_form.is_valid():
            raise ValidationError(password_reset_form.errors)

        return data


class ProfilePictureSerializer(serializers.ModelSerializer):
    profile_img = serializers.CharField()

    class Meta:
        model = User
        fields = ("profile_img",)

    def update(self, instance, validated_data):
        print("Update method called")
        profile_img = validated_data.get("profile_img", None)

        if profile_img:
            # Decode the base64-encoded image data
            format, imgstr = profile_img.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"{instance.username}_profile.{ext}")

            # Update the user's profile image field
            instance.profile_img = data
            instance.save()
        return instance
