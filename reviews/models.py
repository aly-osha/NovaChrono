"""
reviews/models.py — schema table 17.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


class Review(models.Model):
    """Schema table: reviews.

    The schema column is review_text; the Python attribute stays `comment`
    so templates keep working. UNIQUE(user_id, catalog_item_id) enforces one
    review per buyer per item (schema rule 7).
    """
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="reviews",
    )
    rating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # schema rule 8: 1-5
    comment = models.TextField(
        blank=True, default="", db_column="review_text"
    )
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    admin_response = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        ordering = ["-created_at"]
        unique_together = ("buyer", "product")
        indexes = [
            models.Index(fields=["product", "is_approved"]),
        ]

    def __str__(self):
        return f"{self.buyer.email} — {self.product.name} ⭐{self.rating}"

    def save(self, *args, **kwargs):
        # Keep the moderation status flag and the schema's status column
        # from drifting apart.
        if not self.is_approved and self.status == "approved":
            self.status = "pending"
        elif self.is_approved and self.status == "pending":
            self.status = "approved"
        super().save(*args, **kwargs)

    @property
    def review_text(self):
        """Schema column name."""
        return self.comment
