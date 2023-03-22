from django.db import models


# Create your models here.
class Bank(models.Model):
    name = models.CharField(max_length=255)
    issuer_id = models.CharField(max_length=50)

    def __str__(self):
        return self.name
