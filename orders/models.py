from django.db import models
from django.conf import settings
from decimal import Decimal
from catalog.models import Product


class StoreSettings(models.Model):
    store_name = models.CharField(max_length=150, default='NOVACHRONO')
    tagline = models.CharField(max_length=200, default='Collect. Discover. Trade.')
    address_line1 = models.CharField(max_length=255, default='742 Nebula Way, Suite 400')
    address_line2 = models.CharField(max_length=255, blank=True, default='Collectors District')
    city = models.CharField(max_length=100, default='San Francisco')
    state = models.CharField(max_length=100, default='CA')
    postal_code = models.CharField(max_length=20, default='94107')
    country = models.CharField(max_length=100, default='United States')
    email = models.EmailField(default='support@novachrono.com')
    phone = models.CharField(max_length=30, default='+1 (800) 555-CHRONO')
    website = models.URLField(default='https://novachrono.com')
    tax_id = models.CharField(max_length=50, default='US-EIN-94-2849201')
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('7.00'))
    invoice_prefix = models.CharField(max_length=20, default='NC-2026-')
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('150.00'))
    standard_shipping_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('9.99'))

    class Meta:
        verbose_name = 'Store Settings'
        verbose_name_plural = 'Store Settings'

    @classmethod
    def get_settings(cls):
        settings_obj, _ = cls.objects.get_or_create(id=1)
        return settings_obj

    def __str__(self):
        return f"{self.store_name} Settings"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PROCESSING = 'PROCESSING', 'Processing'
        PACKED = 'PACKED', 'Packed'
        SHIPPED = 'SHIPPED', 'Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=50, blank=True, default='')

    # Shipping details snapshot
    shipping_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=25)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True, default='')
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default='United States')

    # Billing details snapshot
    billing_name = models.CharField(max_length=150, blank=True, default='')
    billing_address = models.TextField(blank=True, default='')

    # Delivery & Tracking
    carrier = models.CharField(max_length=100, default='NovaChrono Vault Express / DHL')
    tracking_number = models.CharField(max_length=100, blank=True, default='')
    customer_notes = models.TextField(blank=True, default='')
    admin_notes = models.TextField(blank=True, default='')

    # Cancellation
    cancellation_reason = models.TextField(blank=True, default='')
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_orders'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order #{self.order_number} - {self.user.username} (${self.total_amount})"

    @property
    def can_cancel(self):
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def full_shipping_address(self):
        parts = [
            self.shipping_name,
            self.shipping_address_line1,
            self.shipping_address_line2,
            f"{self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}",
            self.shipping_country,
            f"Phone: {self.shipping_phone}"
        ]
        return "\n".join([p for p in parts if p])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    product_name_snapshot = models.CharField(max_length=255)
    sku_snapshot = models.CharField(max_length=100)
    tcg_snapshot = models.CharField(max_length=100, blank=True, default='')
    condition_snapshot = models.CharField(max_length=100, blank=True, default='')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product_name_snapshot} (${self.subtotal})"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    note = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.order.order_number}: {self.previous_status} -> {self.new_status}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CREDIT_CARD = 'CREDIT_CARD', 'Credit / Debit Card'
        CHRONO_VAULT = 'CHRONO_VAULT', 'NovaChrono Vault Pay'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Direct Collector Wire'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        AUTHORIZED = 'AUTHORIZED', 'Authorized'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partially Refunded'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=30, choices=Method.choices, default=Method.CREDIT_CARD)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PAID)
    transaction_reference = models.CharField(max_length=100, blank=True, default='')
    card_brand = models.CharField(max_length=50, default='Visa Platinum')
    card_last4 = models.CharField(max_length=4, default='4242')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.payment_id} - {self.get_status_display()} (${self.amount})"


class Invoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)

    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=30)
    shipping_address = models.TextField()
    billing_address = models.TextField()

    # Store snapshot details
    store_name = models.CharField(max_length=150)
    store_address = models.TextField()
    store_tax_id = models.CharField(max_length=50)
    store_email = models.EmailField()
    store_phone = models.CharField(max_length=30)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number} (Order {self.order.order_number})"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    tcg = models.CharField(max_length=100, blank=True, default='')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product_name} on Invoice {self.invoice.invoice_number}"


class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        RECEIVED = 'RECEIVED', 'Received'
        COMPLETED = 'COMPLETED', 'Completed'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return #{self.id} for Order {self.order.order_number}"


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=30, default='COMPLETED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund of ${self.amount} for Order {self.order.order_number}"
