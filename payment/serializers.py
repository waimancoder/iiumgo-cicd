from pkg_resources import register_loader_type
from rest_framework import serializers
from .models import Bill


class CreateBillSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ["billpaymentAmount", "billPaymentDate", "billpaymentInvoiceNo", "billExternalReferenceNo"]
