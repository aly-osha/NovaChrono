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
    issue_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="valid",
    )
    qr_code_url = models.CharField(max_length=500, blank=True, default="")
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="issued_certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "authenticity_certificates"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.verification_code} — {self.product.name}"

    def save(self, *args, **kwargs):
        # issue_date defaults to the issued_at date when not supplied.
        if not self.issue_date:
            from django.utils import timezone
            self.issue_date = timezone.now().date()
        # certificate_number is UNIQUE in the schema, so it must be populated
        # on every insert. It is derived from verification_code, which the
        # view sets before saving. The guard below keeps the column unique
        # even when verification_code is assigned after construction.
        if not self.certificate_number and self.verification_code:
            self.certificate_number = f"NC-{self.verification_code}"
        # Keep the schema's status column and the is_active flag in sync.
        if not self.is_active or self.status in ("revoked", "expired"):
            self.is_active = False
            if self.status == "valid":
                self.status = "revoked"
        elif self.status == "valid":
            self.is_active = True
        super().save(*args, **kwargs)
