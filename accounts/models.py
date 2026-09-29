"""
accounts/models.py — Custom User + addresses
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("buyer", "Buyer"),
        ("admin", "Admin"),
        ("super_admin", "Super Admin"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="buyer")
    phone = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)
    # Full name for display (separate from AbstractUser.first_name/last_name)
    name = models.CharField(max_length=150, blank=True, default="")

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name or self.username} ({self.email})"

    def get_full_name(self):
        """Return the display name."""
        return self.name or self.get_username()

    def get_short_name(self):
        return self.name or self.get_username()


class Address(models.Model):
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses"
    )
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "addresses"

    def __str__(self):
        return f"{self.line1}, {self.city} — {self.buyer.email}"
