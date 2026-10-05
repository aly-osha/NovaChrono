"""
wishlists/models.py — schema tables 12 and 13.

The schema splits wishlisting into a parent/child pair:
  wishlists      (wishlist_id, user_id UNIQUE, created_at, updated_at)
  wishlist_items (wishlist_item_id, wishlist_id FK, catalog_item_id FK,
                  added_at)

This is the structural change from the old single `wishlist_items` table
that pointed straight at the user. Rule 10 of the schema also makes wishlist
membership the activator for price-drop and restock monitoring, so
WishlistItem is what monitoring subscribes to.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Wishlist(models.Model):
    """Schema table: wishlists — exactly one wishlist per user."""
    buyer = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="wishlist_record",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wishlists"

    def __str__(self):
        return f"Wishlist — {self.buyer.email}"

    @property
    def item_count(self):
        return self.items.count()


class WishlistItem(models.Model):
    """Schema table: wishlist_items.

    UNIQUE(wishlist_id, catalog_item_id) prevents duplicate rows, and
    membership is what enables price-drop / restock monitoring.
    """
    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name="items",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="wishlist_items",
    )
    # Price at the moment the buyer started watching. This is an immutable
    # baseline: monitoring never overwrites it, so the wishlist can show the
    # original price struck through against the current one.
    added_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    was_out_of_stock = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlist_items"
        unique_together = ("wishlist", "product")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.wishlist.buyer.email} → {self.product.name}"

    @property
    def buyer(self):
        """Compatibility accessor — views/templates used WishlistItem.buyer."""
        return self.wishlist.buyer

    @property
    def is_price_drop(self):
        """True when current price is below the price at watch time."""
        if self.added_price is None:
            return False
        return self.product.price < self.added_price

    @property
    def is_back_in_stock(self):
        return self.product.is_available
