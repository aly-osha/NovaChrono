"""
products/models.py — catalogue taxonomy + sellable items.

Physical schema follows NovaChrono_Database_Schema (20-table design):
  games, sets, categories, catalog_items, catalog_item_images,
  sealed_packs, single_cards

Python attribute names are deliberately unchanged (Product, stock,
sort_order, SingleCardDetail) so every existing template and view keeps
working. The *database* columns match the schema doc via db_column and
db_table. Nothing in templates/ or static/ was modified.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Game(models.Model):
    """Schema table: games (game_id, name UNIQUE, description, is_active, ts)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games"
        verbose_name_plural = "Games"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def active_product_count(self):
        return Product.objects.filter(game=self, is_active=True).count()


class Category(models.Model):
    """Schema table: categories — flat classification, no self-FK parent."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        """Kept for template compatibility now that categories are flat."""
        return self.name


class Set(models.Model):
    """Schema table: sets (set_id, game_id FK, name, code, release_date, ...)."""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="sets")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True, default="")
    release_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sets"
        ordering = ["name"]

    def __str__(self):
        return f"{self.game.name} — {self.name}"


PRODUCT_TYPE_CHOICES = [
    ("sealed", "Sealed Product"),
    ("single_card", "Single Card"),
    ("related", "Related Product"),
]

CONDITION_CHOICES = [
    ("near_mint", "Near Mint"),
    ("lightly_played", "Lightly Played"),
    ("moderately_played", "Moderately Played"),
    ("heavily_played", "Heavily Played"),
    ("damaged", "Damaged"),
]


class Product(models.Model):
    """Schema table: catalog_items.

    The schema names this table catalog_items and requires category_id and
    game_id NOT NULL. It also models game membership directly on the item
    rather than only via set, so `game` is a real FK here. The Python class
    keeps the name `Product` because 24 templates and every view use it.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    # schema column is stock_quantity; attribute stays `stock` for templates
    stock = models.IntegerField(
        default=0, db_column="stock_quantity", validators=[MinValueValidator(0)]
    )
    product_type = models.CharField(
        max_length=20, choices=PRODUCT_TYPE_CHOICES, default="sealed",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products",
    )
    game = models.ForeignKey(
        Game, on_delete=models.PROTECT, related_name="products",
    )
    set = models.ForeignKey(
        Set, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_items"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "product_type"]),
            models.Index(fields=["game", "set"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.stock > 0 and self.is_active

    @property
    def avg_rating(self):
        if hasattr(self, "annotated_rating") and self.annotated_rating is not None:
            return self.annotated_rating
        reviews = self.reviews.filter(is_approved=True)
        return reviews.aggregate(avg=models.Avg("rating"))["avg"]

    @property
    def active_certificate(self):
        return self.certificates.filter(is_active=True).first()

    @property
    def primary_image(self):
        imgs = self.images.all()
        return imgs[0] if imgs else None


class SealedPack(models.Model):
    """Schema table: sealed_packs — one-to-one marker for sealed products.

    The doc keeps this table deliberately sparse: it records only that a
    catalogue item IS a sealed pack, so sealed_packs and single_cards form a
    specialization over catalog_items.
    """
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True,
        related_name="sealed_pack",
    )

    class Meta:
        db_table = "sealed_packs"

    def __str__(self):
        return f"Sealed pack — {self.product.name}"


class SingleCardDetail(models.Model):
    """Schema table: single_cards (card_number, rarity, language, condition)."""
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True,
        related_name="single_card",
    )
    card_number = models.CharField(max_length=50, blank=True, default="")
    rarity = models.CharField(max_length=100, blank=True, default="")
    language = models.CharField(max_length=50, blank=True, default="")
    condition = models.CharField(
        max_length=50, choices=CONDITION_CHOICES, blank=True, default="",
    )

    class Meta:
        db_table = "single_cards"

    def __str__(self):
        return f"{self.product.name} [{self.get_condition_display()}]"


class ProductImage(models.Model):
    """Schema table: catalog_item_images (image, display_order)."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images",
    )
    image = models.ImageField(upload_to="products/")
    # schema column is display_order; attribute stays sort_order
    sort_order = models.IntegerField(default=0, db_column="display_order")

    class Meta:
        db_table = "catalog_item_images"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.product.name} image"


# NOTE: PriceAlert is intentionally removed.
# Database schema rule 10: "No separate price_alerts or restock_alerts tables:
# wishlist membership activates monitoring." Price-drop and restock
# monitoring is now derived from wishlist membership — see
# wishlists/models.py: WishlistItem and Notification.
