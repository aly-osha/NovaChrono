"""
orders/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

STATUS_CHOICES = [
    ("placed", "Placed"),
    ("packed", "Packed"),
    ("shipped", "Shipped"),
    ("delivered", "Delivered"),
    ("cancelled", "Cancelled"),
]

PAYMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("success", "Success"),
    ("failed", "Failed"),
]

PAYMENT_METHOD_CHOICES = [
    ("card", "Card"),
    ("upi", "UPI"),
    ("sandbox", "Sandbox"),
]


class Order(models.Model):
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders",
    )
    shipping_address = models.ForeignKey(
        "accounts.Address", on_delete=models.PROTECT, related_name="orders",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="placed",
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} — {self.buyer.email} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, related_name="order_items",
    )
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment",
    )
    method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    transaction_ref = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending",
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment #{self.pk} — {self.get_status_display()}"
