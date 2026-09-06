from django.db import models
from django.conf import settings
from decimal import Decimal
from catalog.models import Product, Promotion


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts'
    )
    session_key = models.CharField(max_length=50, blank=True, default='')
    coupon = models.ForeignKey(Promotion, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = self.user.username if self.user else f"Guest ({self.session_key[:8]})"
        return f"Cart #{self.id} for {owner}"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.select_related('product'))

    @property
    def discount_amount(self):
        if not self.coupon or not self.coupon.is_active:
            return Decimal('0.00')
        sub = self.subtotal
        if sub < self.coupon.minimum_spend:
            return Decimal('0.00')
        if self.coupon.discount_percentage > Decimal('0.00'):
            return round((sub * self.coupon.discount_percentage) / Decimal('100.00'), 2)
        return min(self.coupon.discount_amount, sub)

    @property
    def shipping_amount(self):
        # Free shipping on orders over $150
        if self.subtotal >= Decimal('150.00') or self.subtotal == Decimal('0.00'):
            return Decimal('0.00')
        return Decimal('9.99')

    @property
    def tax_amount(self):
        # Standard estimated tax rate 7%
        taxable_amount = max(Decimal('0.00'), self.subtotal - self.discount_amount)
        return round(taxable_amount * Decimal('0.07'), 2)

    @property
    def total(self):
        return max(Decimal('0.00'), self.subtotal - self.discount_amount + self.shipping_amount + self.tax_amount)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')
        ordering = ['added_at']

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
