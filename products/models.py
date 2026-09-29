"""
products/models.py
"""
from django.db import models


class Game(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "games"
        verbose_name_plural = "Games"

    def __str__(self):
        return self.name

    @property
    def active_product_count(self):
        return Product.objects.filter(set__game=self, is_active=True).count()


class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        parts = []
        node = self
        while node:
            parts.append(node.name)
            node = node.parent
        return " ≫ ".join(reversed(parts))


class Set(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="sets")
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "sets"

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
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    product_type = models.CharField(
        max_length=20, choices=PRODUCT_TYPE_CHOICES, default="sealed",
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    set = models.ForeignKey(
        Set, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.stock > 0 and self.is_active

    @property
    def avg_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if not reviews.exists():
            return None
        return reviews.aggregate(avg=models.Avg("rating"))["avg"]

    @property
    def active_certificate(self):
        return self.certificates.filter(is_active=True).first()


class SingleCardDetail(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True,
        related_name="single_card",
    )
    rarity = models.CharField(max_length=50, blank=True, default="")
    language = models.CharField(max_length=50, blank=True, default="")
    condition = models.CharField(
        max_length=30, choices=CONDITION_CHOICES, blank=True, default="",
    )

    class Meta:
        db_table = "single_card_details"

    def __str__(self):
        return f"{self.product.name} [{self.get_condition_display()}]"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images",
    )
    image = models.ImageField(upload_to="products/")
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.product.name} image"


class PriceAlert(models.Model):
    """Buyer price-drop watch: notify when product hits target price (FR-21/22)."""
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="price_alerts",
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="price_alerts",
    )
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "price_alerts"
        unique_together = ("buyer", "product")

    def __str__(self):
        return f"{self.buyer.email} watches {self.product.name} @ ₹{self.target_price}"
