from django.contrib import admin

from .models import Product, Game, Set, Category, SingleCardDetail, ProductImage, SealedPack


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "sets_count")
    search_fields = ("name",)

    def sets_count(self, obj):
        return obj.sets.count()
    sets_count.short_description = "Sets"


@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    list_display = ("name", "game")
    list_filter = ("game",)
    search_fields = ("name", "game__name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "product_type", "price", "stock", "is_active", "created_at")
    list_filter = ("product_type", "is_active")
    search_fields = ("name", "description")
    list_editable = ("price", "stock")


@admin.register(SingleCardDetail)
class SingleCardDetailAdmin(admin.ModelAdmin):
    list_display = ("product", "rarity", "language", "condition")
    list_filter = ("condition", "rarity")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "sort_order")
    list_filter = ("product",)


# NOTE: PriceAlert admin is removed. Schema rule 10 bans the price_alerts
# table — monitoring derives from wishlist membership. See
# wishlists/admin.py for the WishlistItem admin instead.
