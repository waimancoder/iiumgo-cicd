from django.urls import path
from . import views

urlpatterns = [
    path("api/fpx-payment-methods/", views.FPXPaymentMethods.as_view(), name="fpx_payment_methods"),
    # path("process-selected-bank/", views.ProcessSelectedBank.as_view(), name="process_selected_bank"),
    path("api/fpx-payment", views.MakePayment.as_view(), name="fpx_payment"),
    path("api/payment_return", views.ToyyibPayReturnAPIView.as_view(), name="payment_return"),
    path("api/payment_callback", views.ToyyibPayCallbackAPIView.as_view(), name="payment_callback"),
    path("api/create-bill", views.CreateBillAPIView.as_view(), name="create_bill"),
    path("api/driver_ewallet/<uuid:user_id>", views.DriverEwalletView.as_view(), name="driver_ewallet"),
    path("api/top_up_history/<uuid:user_id>", views.BillHistoryAPIView.as_view(), name="top_up_history"),
]
