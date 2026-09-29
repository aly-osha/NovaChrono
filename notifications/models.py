"""
notifications/models.py — schema table 19.

notifications (notification_id, user_id FK, notification_type, title,
message, is_read, created_at)

Per schema rule 10 there is no separate price_alerts or restock_alerts
table: a buyer watching a product is simply a WishlistItem, and the events
that monitoring produces land here as price_drop / restock notifications
(FR-22, FR-23, FR-25).
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

NOTIFICATION_TYPE_CHOICES = [
    ("price_drop", "Price drop"),
    ("restock", "Back in stock"),
    ("order_update", "Order update"),
    ("review", "Review activity"),
    ("system", "System"),
]


class Notification(models.Model):
    """Schema table: notifications."""
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30, choices=NOTIFICATION_TYPE_CHOICES, default="system",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["buyer", "is_read"]),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} — {self.title}"

    @property
    def user(self):
        """Schema column is user_id; `user` reads better at call sites."""
        return self.buyer
