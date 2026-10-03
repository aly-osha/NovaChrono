"""
cart/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Cart(models.Model):
    """Schema table: carts (cart_id, user_id UNIQUE, created_at, updated_at)."""
    buyer = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart — {self.buyer.email}"

    @property
    def subtotal(self):
        return sum(
            item.product.price * item.quantity for item in self.items.all()
        )

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="cart_items",
    )
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity


# NOTE: WishlistItem moved to the `wishlists` app.
# The schema splits wishlisting into two tables — wishlists (one per user)
# and wishlist_items (many per wishlist) — rather than pointing items
# straight at the user. See wishlists/models.py.
