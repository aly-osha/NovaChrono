from django.contrib import admin

from .models import Order, OrderItem, Payment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "buyer", "status", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("buyer__email",)
    date_hierarchy = "created_at"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "unit_price")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "status", "transaction_ref")
    list_filter = ("status", "method")
