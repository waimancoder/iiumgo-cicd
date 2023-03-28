from pyexpat import model
from django.db import models
import uuid


# Create your models here.
class DriverEwallet(models.Model):
    driver_id = models.OneToOneField(
        "user_account.User", on_delete=models.CASCADE, primary_key=True, related_name="ewallet"
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="MYR")


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("user_account.User", on_delete=models.CASCADE)
    billCode = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="MYR")
    payment_method = models.CharField(max_length=50, default="fpx")
    payment_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    refno = models.CharField(max_length=255, blank=True, null=True)
    order_id = models.CharField(max_length=255, blank=True, null=True)
    bill = models.OneToOneField("Bill", on_delete=models.CASCADE, null=True, blank=True, related_name="billpertrans")

    def save(self, *args, **kwargs):
        if not self.bill:
            self.bill = Bill.objects.create(payment=self, billCode=self.billCode)
        super().save(*args, **kwargs)


class Bill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="paymentpertrans", default="")
    billCode = models.CharField(max_length=50, blank=True, null=True)
    billName = models.CharField(max_length=255, blank=True, null=True)
    billDescription = models.CharField(max_length=255, blank=True, null=True)
    billTo = models.CharField(max_length=255, blank=True, null=True)
    billEmail = models.EmailField(blank=True, null=True)
    billPhone = models.CharField(max_length=255, blank=True, null=True)
    billStatus = models.CharField(max_length=255, blank=True, null=True)
    billpaymentStatus = models.CharField(max_length=255, blank=True, null=True)
    billpaymentChannel = models.CharField(max_length=255, blank=True, null=True)
    billpaymentAmount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    billpaymentInvoiceNo = models.CharField(max_length=255, blank=True, null=True)
    billSplitPayment = models.CharField(max_length=255, blank=True, null=True)
    billSplitPaymentArgs = models.TextField(blank=True, null=True)
    billpaymentSettlement = models.CharField(max_length=255, blank=True, null=True)
    billpaymentSettlementDate = models.DateTimeField(blank=True, null=True)
    SettlementReferenceNo = models.CharField(max_length=255, blank=True, null=True)
    billPaymentDate = models.DateTimeField(blank=True, null=True)
    billExternalReferenceNo = models.CharField(max_length=255, blank=True, null=True)
