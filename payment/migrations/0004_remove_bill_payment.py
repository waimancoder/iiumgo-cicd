# Generated by Django 4.1.6 on 2023-03-28 10:40

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0003_remove_payment_bill_alter_bill_payment"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bill",
            name="payment",
        ),
    ]