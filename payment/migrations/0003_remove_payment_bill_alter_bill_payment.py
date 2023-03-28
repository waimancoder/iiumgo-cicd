# Generated by Django 4.1.6 on 2023-03-28 10:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0002_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="payment",
            name="bill",
        ),
        migrations.AlterField(
            model_name="bill",
            name="payment",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="paymentpertrans",
                to="payment.payment",
            ),
        ),
    ]
