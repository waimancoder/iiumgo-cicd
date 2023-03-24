# payment.py

import json
import os
import Adyen


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


# request = {
#     "merchantAccount": adyen.merchant_account,
#     "countryCode": "MY",
#     "shopperLocale": "en-US",
#     "amount": {"value": 1000, "currency": "MYR"},
#     "channel": "Web",
# }
# payment_methods_result = adyen.checkout.payments_api.payment_methods(request)

# {
#     "message": {
#         "paymentMethods": [
#             {
#                 "issuers": [
#                     {"id": "fpx_mb2u", "name": "Maybank2u"},
#                     {"id": "fpx_cimbclicks", "name": "CIMB Clicks"},
#                     {"id": "fpx_bimb", "name": "Bank Islam"},
#                     {"id": "fpx_pbb", "name": "Public Bank"},
#                     {"id": "fpx_abb", "name": "Affin Bank"},
#                     {"id": "fpx_agrobank", "name": "Agrobank"},
#                     {"id": "fpx_abmb", "name": "Alliance Bank"},
#                     {"id": "fpx_amb", "name": "Am Online"},
#                     {"id": "fpx_bmmb", "name": "Bank Muamalat"},
#                     {"id": "fpx_bkrm", "name": "Bank Rakyat"},
#                     {"id": "fpx_bsn", "name": "Bank Simpanan Nasional"},
#                     {"id": "fpx_hlb", "name": "Hong Leong Connect"},
#                     {"id": "fpx_hsbc", "name": "HSBC"},
#                     {"id": "fpx_kfh", "name": "Kuwait Finance House"},
#                     {"id": "fpx_ocbc", "name": "OCBC Bank"},
#                     {"id": "fpx_rhb", "name": "RHB Now"},
#                     {"id": "fpx_scb", "name": "Standard Chartered Bank"},
#                     {"id": "fpx_uob", "name": "UOB Bank"},
#                 ],
#                 "name": "Malaysia E-Banking",
#                 "type": "molpay_ebanking_fpx_MY",
#             }
#         ]
#     },
#     "status_code": 200,
#     "psp": "WVSHFLD3NQRXGN82",
#     "raw_request": {
#         "merchantAccount": "UnigoLtd_IIUMGO_TEST",
#         "countryCode": "MY",
#         "shopperLocale": "en-US",
#         "amount": {"value": 1000, "currency": "MYR"},
#         "channel": "Web",
#     },
#     "raw_response": '{"paymentMethods":[{"issuers":[{"id":"fpx_mb2u","name":"Maybank2u"},{"id":"fpx_cimbclicks","name":"CIMB Clicks"},{"id":"fpx_bimb","name":"Bank Islam"},{"id":"fpx_pbb","name":"Public Bank"},{"id":"fpx_abb","name":"Affin Bank"},{"id":"fpx_agrobank","name":"Agrobank"},{"id":"fpx_abmb","name":"Alliance Bank"},{"id":"fpx_amb","name":"Am Online"},{"id":"fpx_bmmb","name":"Bank Muamalat"},{"id":"fpx_bkrm","name":"Bank Rakyat"},{"id":"fpx_bsn","name":"Bank Simpanan Nasional"},{"id":"fpx_hlb","name":"Hong Leong Connect"},{"id":"fpx_hsbc","name":"HSBC"},{"id":"fpx_kfh","name":"Kuwait Finance House"},{"id":"fpx_ocbc","name":"OCBC Bank"},{"id":"fpx_rhb","name":"RHB Now"},{"id":"fpx_scb","name":"Standard Chartered Bank"},{"id":"fpx_uob","name":"UOB Bank"}],"name":"Malaysia E-Banking","type":"molpay_ebanking_fpx_MY"}]}',
#     "details": {},
# }
