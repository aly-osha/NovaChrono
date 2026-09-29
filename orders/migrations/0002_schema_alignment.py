"""
Align orders schema with NovaChrono_Database_Schema (tables 14-16).

orders:
  + immutable shipping_* address snapshot (schema rule 9)
  + order_date, updated_at
  shipping_address FK retained (doc requires address_id) and drives the
  snapshot via Order.save().

order_items:
  + subtotal (derived in save()), UNIQUE(order, product)  (schema rule 5)
  + quantity CHECK > 0  (schema rule 3)

payments:
  method     -> db_column payment_method
  status     -> db_column payment_status
  transaction_ref -> db_column transaction_reference (UNIQUE)
  + amount, created_at, updated_at
"""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_schema_alignment"),
        ("orders", "0001_initial"),
        ("products", "0003_schema_alignment"),
    ]

    operations = [
        # ---- orders: shipping snapshot + timestamps ----
        migrations.AddField(
            model_name="order",
            name="shipping_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_address_line1",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_address_line2",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_city",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_state",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_postal_code",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_country",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="order_date",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),

        # ---- order_items: subtotal + uniqueness + quantity validation ----
        migrations.AddField(
            model_name="orderitem",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="quantity",
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterUniqueTogether(
            name="orderitem",
            unique_together={("order", "product")},
        ),

        # ---- payments: schema column names + amount + timestamps ----
        migrations.AlterField(
            model_name="payment",
            name="method",
            field=models.CharField(
                choices=[("card", "Card"), ("upi", "UPI"), ("sandbox", "Sandbox")],
                db_column="payment_method",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("success", "Success"),
                    ("failed", "Failed"),
                ],
                db_column="payment_status",
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="transaction_ref",
            field=models.CharField(
                blank=True,
                db_column="transaction_reference",
                default="",
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]
