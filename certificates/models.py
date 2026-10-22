"""
certificates/models.py — schema table 18.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

STATUS_CHOICES = [
    ("valid", "Valid"),
    ("revoked", "Revoked"),
    ("expired", "Expired"),
]


class AuthenticityCertificate(models.Model):
    """Schema table: authenticity_certificates.

    Adds certificate_number and issue_date per the schema. The existing
    verification_code, qr_code_url, issued_by, issued_at and is_active fields
    are retained because FR-50..FR-58 depend on them (public verification
    page, QR representation, revocation).
    """
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="certificates",
    )
    certificate_number = models.CharField(
        max_length=100, unique=True, blank=True, default=""
    )
    verification_code = models.CharField(
        max_length=100, unique=True, db_column="verification_code",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="valid",
    )
    qr_code_url = models.CharField(max_length=500, blank=True, default="")
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="issued_certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "authenticity_certificates"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.verification_code} — {self.product.name}"

    @property
    def is_active(self):
        return self.status == "valid"

    @property
    def issue_date(self):
        return self.issued_at.date() if self.issued_at else None

    def save(self, *args, **kwargs):
        # certificate_number is UNIQUE in the schema, so it must be populated
        # on every insert. It is derived from verification_code, which the
        # view sets before saving. The guard below keeps the column unique
        # even when verification_code is assigned after construction.
        if not self.certificate_number and self.verification_code:
            self.certificate_number = f"NC-{self.verification_code}"
        super().save(*args, **kwargs)
