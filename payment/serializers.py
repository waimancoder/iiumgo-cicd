from pkg_resources import register_loader_type
from rest_framework import serializers
from .models import Bill


class CreateBillSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class BillSerializer(serializers.ModelSerializer):
    payment_amount = serializers.DecimalField(source="billpaymentAmount", max_digits=10, decimal_places=2)
    payment_date = serializers.DateTimeField(source="billPaymentDate")
    transaction_id = serializers.CharField(source="billpaymentInvoiceNo")
    reference_no = serializers.CharField(source="billExternalReferenceNo")

    class Meta:
        model = Bill
        fields = ["payment_amount", "payment_date", "transaction_id", "reference_no"]
