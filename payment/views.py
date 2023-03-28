import hashlib
import json
import os
from uuid import uuid4
from django.shortcuts import render
from django.urls import reverse
from rest_framework import status
from rest_framework import exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from payment.serializers import CreateBillSerializer

from user_account.models import User
from .payment import get_adyen_client, get_payment_methods, get_fpx_banks, get_issuer_id, make_fpx_payment
from django.http import HttpRequest
from django.http import JsonResponse
import requests


def get_current_domain(request: HttpRequest) -> str:
    """
    Get the domain name for the current request.
    """
    return request.META.get("HTTP_HOST", "")


class FPXPaymentMethods(APIView):
    def get(self, request):
        try:
            # Replace with your API key and merchant account
            api_key = os.environ.get("ADYEN_API_KEY")
            merchant_account = os.environ.get("ADYEN_MERCHANT_ACCOUNT")
            adyen_client = get_adyen_client(api_key, merchant_account)
            payment_methods = get_payment_methods(adyen_client, "MY", "en-US", 1000, "MYR", "Web")
            fpx_banks = get_fpx_banks(payment_methods)

            return Response(
                {"success": True, "statusCode": status.HTTP_200_OK, "banks": fpx_banks}, status=status.HTTP_200_OK
            )
        except Exception as e:
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


class MakePayment(APIView):
    def post(self, request):
        try:
            order_number = 100
            amount = request.data["amount"]
            currency = request.data["currency"]
            issuer = request.data["issuer"]
            return_url = request.build_absolute_uri(reverse("payment_return"))

            result = make_fpx_payment(order_number, amount, currency, issuer, return_url)
            result_dict = result.__dict__

            response_data = result_dict["message"]

            return Response(
                {"success": True, "statusCode": status.HTTP_200_OK, "data": result_dict}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def payment_return(request):
    return JsonResponse({"status": "success", "message": "Payment processed successfully"})


class CreateBillAPIView(APIView):
    serializer_class = CreateBillSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            user_id = validated_data["user_id"]
            amount = validated_data["amount"]
            return_url = request.build_absolute_uri(reverse("payment_return"))

            ref_number = uuid4()
            user = User.objects.get(id=user_id)
            billName = f"DE-{user.username}"
            billName = f"DE-{user.username}"
            if len(billName) > 30:
                billName = billName[:30]
            billName = billName.rstrip()
            billDescriptionHash = f"DE-{user.id}{ref_number}{amount}"
            billDescription = hashlib.sha256(billDescriptionHash.encode("utf-8")).hexdigest()

            amount_in_cents = int(amount * 100)
            request = {
                "userSecretKey": os.environ.get("userSecretKey"),
                "categoryCode": "55j6xxn1",
                "billName": billName,
                "billDescription": billDescription,
                "billPriceSetting": 1,
                "billPayorInfo": 0,
                "billAmount": {amount_in_cents},
                "billCallbackUrl": return_url,
                "billExternalReferenceNo": ref_number,
                "billTo": user.fullname,
                "billEmail": user.email,
                "billPhone": user.phone_no,
            }

            response = requests.post("https://dev.toyyibpay.com/index.php/api/createBill", data=request)
            response_data = response.json()
            print(response_data)
            bill_code = response_data[0]["BillCode"]
            payment_url = f"https://dev.toyyibpay.com/{bill_code}"
            data = {
                "payment_url": payment_url,
            }

            return Response(
                {"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK
            )
        except Exception as e:
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
