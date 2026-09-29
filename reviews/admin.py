from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("pk", "product", "buyer", "rating", "is_verified_purchase", "is_approved", "created_at")
    list_filter = ("is_approved", "is_verified_purchase", "product")
    search_fields = ("buyer__email", "comment")
    date_hierarchy = "created_at"
