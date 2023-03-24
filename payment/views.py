import os
from django.shortcuts import render
from rest_framework import status
from rest_framework import exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from .payment import get_adyen_client, get_payment_methods, get_fpx_banks, get_issuer_id, make_fpx_payment


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
            order_number = 1
            amount = request.data["amount"]
            currency = request.data["currency"]
            issuer = request.data["issuer"]
            return_url = "https://localhost:8000/"

            result = make_fpx_payment(order_number, amount, currency, issuer, return_url)
            result_dict = result.__dict__

            response_data = result_dict["message"]

            return Response(
                {"success": True, "statusCode": status.HTTP_200_OK, "data": response_data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
