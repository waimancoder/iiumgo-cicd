from django.db import models


# Create your models here.
class Bank(models.Model):
    name = models.CharField(max_length=255)
    issuer_id = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Payment(models.Model):
    order_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    issuer = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.order_number
