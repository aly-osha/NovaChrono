from django.contrib import admin

from .models import Wishlist, WishlistItem


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("buyer", "item_count", "created_at")
    search_fields = ("buyer__email",)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    # Schema rule 10: wishlist membership IS the price-drop / restock
    # subscription, so there is no separate price_alerts table to manage.
    list_display = ("product", "added_price", "current_price", "added_at")
    list_filter = ("added_at",)
    search_fields = ("product__name", "wishlist__buyer__email")

    @admin.display(description="current price")
    def current_price(self, obj):
        return obj.product.price
