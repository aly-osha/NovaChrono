"""
accounts/models.py — Custom User + addresses
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Schema table: users.

    The doc describes a single `users` table with role, phone, status and
    timestamps. AbstractUser already supplies first_name/last_name/email/
    password; this adds the doc's role/phone/status plus created_at and
    updated_at. `is_active` (from AbstractUser) is left in place because
    Django's auth machinery requires it — `status` is the business-facing
    field and the two are kept in sync in save().
    """
    ROLE_CHOICES = [
        ("buyer", "Buyer"),
        ("admin", "Admin"),
        ("super_admin", "Super Admin"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="buyer")
    phone = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active",
    )
    # Full name for display (separate from AbstractUser.first_name/last_name)
    name = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name or self.username} ({self.email})"

    def save(self, *args, **kwargs):
        # Keep Django's auth flag and the schema's status column consistent.
        self.is_active = self.status == "active"
        super().save(*args, **kwargs)

    @property
    def user_id(self):
        return self.pk

    def get_full_name(self):
        """Return the display name."""
        return self.name or self.get_username()

    def get_short_name(self):
        return self.name or self.get_username()

    @property
    def is_admin_role(self):
        return self.role in ("admin", "super_admin")


class Address(models.Model):
    """Schema table: addresses.

    Column names follow the doc (address_line1/address_line2); the Python
    attributes stay line1/line2 so existing forms, views and templates are
    untouched. `line1`/`line2` are the real fields and carry the db_column
    mapping to the schema's names.
    """
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses"
    )
    line1 = models.CharField(
        max_length=255, db_column="address_line1"
    )
    line2 = models.CharField(
        max_length=255, blank=True, default="", db_column="address_line2"
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "addresses"
        constraints = [
            # Schema rule 1: only one default address per user.
            models.UniqueConstraint(
                fields=["buyer"],
                condition=models.Q(is_default=True),
                name="uniq_default_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.line1}, {self.city} — {self.buyer.email}"

    @property
    def user(self):
        """Schema column is user_id."""
        return self.buyer

    @property
    def as_dict(self):
        """Snapshot source for the immutable shipping_* fields on Order."""
        return {
            "shipping_name": self.buyer.get_full_name(),
            "shipping_address_line1": self.line1,
            "shipping_address_line2": self.line2,
            "shipping_city": self.city,
            "shipping_state": self.state,
            "shipping_postal_code": self.postal_code,
            "shipping_country": self.country,
        }
