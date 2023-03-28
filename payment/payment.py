# payment.py

import email
import hashlib
import json
import os
from uuid import uuid4
import Adyen
from django.urls import reverse
import requests

from user_account.models import User


# Configure Adyen client
def get_adyen_client(api_key, merchant_account):
    adyen = Adyen.Adyen()
    adyen.payment.client.platform = "test"
    adyen.client.xapikey = api_key
    adyen.payment.client.merchant_account = merchant_account
    return adyen


# Get payment methods
def get_payment_methods(adyen_client, country, shopper_locale, amount, currency, channel):
    request = {
        "merchantAccount": adyen_client.payment.client.merchant_account,
        "countryCode": country,
        "shopperLocale": shopper_locale,
        "amount": {"value": amount, "currency": currency},
        "channel": channel,
    }
    payment_methods_result = adyen_client.checkout.payments_api.payment_methods(request)
    return payment_methods_result.__dict__


# Extract FPX banks from payment methods
def get_fpx_banks(payment_methods_result):
    fpx_banks = {}

    result_dict = payment_methods_result
    fpx_banks = json.loads(result_dict["raw_response"])
    return fpx_banks


# Get the issuer ID for the selected bank
def get_issuer_id(bank_name, fpx_banks):
    for bank in fpx_banks:
        if bank["name"] == bank_name:
            return bank["id"]
    return None


def make_fpx_payment(order_number, amount, currency, issuer, return_url):
    adyen = Adyen.Adyen()
    adyen.client.xapikey = os.environ.get("ADYEN_API_KEY")
    adyen.payment.client.merchant_account = os.environ.get("ADYEN_MERCHANT_ACCOUNT")

    result = adyen.checkout.payments_api.payments(
        {
            "amount": {"value": amount, "currency": currency},
            "countryCode": "MY",
            "shopperLocale": "en-US",
            "reference": order_number,
            "paymentMethod": {"type": "molpay_ebanking_fpx_MY", "issuer": issuer},
            "returnUrl": return_url,
            "merchantAccount": adyen.payment.client.merchant_account,
        }
    )

    return result


def create_bill(user_id, amount, return_url):
    ref_number = uuid4()
    user = User.objects.get(id=user_id)
    billName = f"DriverEwallet-{user.id}{ref_number}{amount}"
    billDescription = hashlib.sha256(billName.encode("utf-8")).hexdigest()

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
        "billPhone": user.phone_number,
    }

    response = requests.post("https://dev.toyyibpay.com/index.php/api/createBill", data=request)
    result = response.text
    obj = json.loads(result)
    print(obj)

    return obj
