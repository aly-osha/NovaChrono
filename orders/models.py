"""
orders/models.py — schema tables 14, 15, 16 (orders, order_items, payments).
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone

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
    ("cod", "Cash on Delivery"),
    ("sandbox", "Sandbox"),
]

# Methods that are collected at the door rather than settled online. An order
# paid by COD is confirmed on placement but its payment is not 'success' until
# the buyer hands over cash — modelled as 'pending' (see orders/views.checkout).
CASH_ON_DELIVERY = "cod"
ONLINE_METHODS = {"card", "upi", "sandbox"}


class Order(models.Model):
    """Schema table: orders.

    The doc requires an immutable checkout-time address snapshot: the
    shipping_* fields are copied from the chosen Address at checkout and
    never updated, so a later address edit cannot rewrite order history
    (schema rule 9).
    """
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders",
    )
    shipping_address = models.ForeignKey(
        "accounts.Address", on_delete=models.PROTECT, related_name="orders",
    )
    # --- immutable snapshot of the address at checkout time ---
    shipping_name = models.CharField(max_length=200, blank=True, default="")
    shipping_address_line1 = models.CharField(
        max_length=255, blank=True, default=""
    )
    shipping_address_line2 = models.CharField(
        max_length=255, blank=True, default=""
    )
    shipping_city = models.CharField(max_length=100, blank=True, default="")
    shipping_state = models.CharField(max_length=100, blank=True, default="")
    shipping_postal_code = models.CharField(
        max_length=20, blank=True, default=""
    )
    shipping_country = models.CharField(max_length=100, blank=True, default="")
    # ------------------------------------------------------
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="placed",
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} — {self.buyer.email} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Populate the snapshot on first save if not already supplied.
        if not self.shipping_address_line1 and self.shipping_address_id:
            for field, value in self.shipping_address.as_dict.items():
                setattr(self, field, value)
        super().save(*args, **kwargs)

    @property
    def shipping_address_display(self):
        """Single-line address for list views and order confirmation."""
        parts = [
            self.shipping_address_line1,
            self.shipping_address_line2,
            self.shipping_city,
            self.shipping_state,
            self.shipping_postal_code,
            self.shipping_country,
        ]
        return ", ".join(p for p in parts if p)


class OrderItem(models.Model):
    """Schema table: order_items (unit_price preserves purchase price)."""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, related_name="order_items",
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "order_items"
        unique_together = ("order", "product")

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    def save(self, *args, **kwargs):
        # subtotal is derived — never trust a posted value (schema rule 5).
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    @property
    def line_total(self):
        return self.subtotal or (self.unit_price * self.quantity)


class Payment(models.Model):
    """Schema table: payments — one payment per order in the mock design.

    The schema names the columns payment_method and payment_status; the
    Python attributes stay `method` and `status` so existing views and
    templates keep working, via db_column mapping.
    """
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment",
    )
    method = models.CharField(
        max_length=30, choices=PAYMENT_METHOD_CHOICES,
        db_column="payment_method",
    )
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending",
        db_column="payment_status",
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    transaction_ref = models.CharField(
        max_length=100, blank=True, default="", unique=True,
        null=True, db_column="transaction_reference",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment #{self.pk} — {self.get_status_display()}"

    @property
    def payment_method(self):
        """Schema column name."""
        return self.method

    @property
    def payment_status(self):
        """Schema column name."""
        return self.status

    @property
    def transaction_reference(self):
        """Schema column name."""
        return self.transaction_ref
