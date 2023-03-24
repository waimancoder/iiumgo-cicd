from django.urls import path
from . import views

urlpatterns = [
    path("api/fpx-payment-methods/", views.FPXPaymentMethods.as_view(), name="fpx_payment_methods"),
    # path("process-selected-bank/", views.ProcessSelectedBank.as_view(), name="process_selected_bank"),
    path("api/fpx-payment", views.MakePayment.as_view(), name="fpx_payment"),
]
