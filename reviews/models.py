"""
reviews/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Review(models.Model):
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="reviews",
    )
    rating = models.SmallIntegerField()  # 1–5
    comment = models.TextField(blank=True, default="")
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    admin_response = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "is_approved"]),
        ]

    def __str__(self):
        return f"{self.buyer.email} — {self.product.name} ⭐{self.rating}"
