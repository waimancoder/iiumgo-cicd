import hashlib
import json
import os
import stat
from uuid import uuid4
from django.shortcuts import render
from django.urls import reverse
from rest_framework import status
from rest_framework import exceptions
from rest_framework.views import APIView, csrf_exempt
from rest_framework.response import Response
from payment.models import Payment
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
            callback_url = request.build_absolute_uri(reverse("payment_callback"))

            print(return_url)

            ref_number = uuid4()
            user = User.objects.get(id=user_id)
            billName = f"DE-{user.username}"
            billName = f"DE-{user.username}"
            if len(billName) > 30:
                billName = billName[:30]
            billName = billName.rstrip()
            billDescription = f"DE-{user.id}{ref_number}{amount}"

            amount_in_cents = int(amount * 100)
            request = {
                "userSecretKey": os.environ.get("userSecretKey"),
                "categoryCode": "55j6xxn1",
                "billName": billName,
                "billDescription": billDescription,
                "billPriceSetting": 1,
                "billPayorInfo": 0,
                "billAmount": {amount_in_cents},
                "billReturnUrl": return_url,
                "billCallbackUrl": callback_url,
                "billExternalReferenceNo": ref_number,
                "billTo": user.fullname,
                "billEmail": user.email,
                "billPhone": user.phone_no,
            }

            response = requests.post("https://dev.toyyibpay.com/index.php/api/createBill", data=request)
            response_data = response.json()
            print(response_data)
            bill_code = response_data[0]["BillCode"]
            Payment.objects.create(
                user_id=user_id,
                amount=amount,
                payment_status="pending",
                billCode=bill_code,
            )
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


class ToyyibPayCallbackAPIView(APIView):
    @csrf_exempt
    def post(self, request):
        refno = request.data.get("refno")
        status = request.data.get("status")
        reason = request.data.get("reason")
        billcode = request.data.get("billcode")
        order_id = request.data.get("order_id")
        amount = request.data.get("amount")
        transaction_time = request.data.get("transaction_time")

        # Implement your callback handling logic here, such as updating the payment status of an order in the database or sending a confirmation email
        # ...
        payment = Payment.objects.get(billCode=billcode)
        if status == "1":
            payment.payment_status = "success"
        elif status == "2":
            payment.payment_status = "pending"
        elif status == "3":
            payment.payment_status = "failed"
        payment.refno = refno
        payment.reason = reason
        payment.order_id = order_id

        payment.save()

        return Response(status=status.HTTP_200_OK)


class ToyyibPayReturnAPIView(APIView):
    def get(self, request):
        status_id = request.query_params.get("status_id")
        billcode = request.query_params.get("billcode")
        order_id = request.query_params.get("order_id")

        # Implement your payment status handling logic here, such as updating the payment status of an order in the database or sending a confirmation email
        # ...
        payment = Payment.objects.get(billCode=billcode)

        data = {
            "user_id": payment.user_id,
            "status_id": status_id,
            "billcode": billcode,
            "order_id": order_id,
            "payment_status": payment.payment_status,
            "amount": payment.amount,
            "refno": payment.refno,
            "reason": payment.reason,
        }

        return Response({"success": True, "statusCode": status.HTTP_200_OK, "data": data}, status=status.HTTP_200_OK)
