from django.contrib import admin

from .models import AuthenticityCertificate


@admin.register(AuthenticityCertificate)
class AuthenticityCertificateAdmin(admin.ModelAdmin):
    list_display = ("verification_code", "product", "status", "issued_at")
    list_filter = ("status",)
    search_fields = ("verification_code", "product__name")
