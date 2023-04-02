from pkg_resources import register_loader_type
from rest_framework import serializers
from .models import Bill, CommissionHistory


class CreateBillSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class BillSerializer(serializers.Serializer):
    type = serializers.CharField()
    payment_amount = serializers.DecimalField(
        source="billpaymentAmount", max_digits=10, decimal_places=2, required=False
    )
    commission_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    payment_date = serializers.DateTimeField(source="billPaymentDate", required=False)
    commission_payment_date = serializers.DateTimeField(source="payment_date", required=False)
    transaction_id = serializers.CharField(source="billpaymentInvoiceNo", required=False)
    reference_no = serializers.CharField(source="billExternalReferenceNo", required=False)

    class Meta:
        fields = [
            "type",
            "payment_amount",
            "commission_amount",
            "payment_date",
            "commission_payment_date",
            "transaction_id",
            "reference_no",
        ]
