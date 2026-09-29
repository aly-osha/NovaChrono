"""
certificates/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthenticityCertificate(models.Model):
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="certificates",
    )
    verification_code = models.CharField(max_length=50, unique=True)
    qr_code_url = models.CharField(max_length=500, blank=True, default="")
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="issued_certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "authenticity_certificates"

    def __str__(self):
        return f"{self.verification_code} — {self.product.name}"
