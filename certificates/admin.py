from django.contrib import admin

from .models import AuthenticityCertificate


@admin.register(AuthenticityCertificate)
class AuthenticityCertificateAdmin(admin.ModelAdmin):
    list_display = ("verification_code", "product", "is_active", "issued_at")
    list_filter = ("is_active",)
    search_fields = ("verification_code", "product__name")
