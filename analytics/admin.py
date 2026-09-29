"""
analytics/admin.py — register ActivityLog, SystemSetting, User, Address.
"""
from django.contrib import admin

from .models import ActivityLog, SystemSetting
from accounts.models import Address, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("get_full_name", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "name", "username")
    ordering = ("-date_joined",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("buyer", "city", "is_default")
    list_filter = ("is_default",)
    search_fields = ("line1", "city", "buyer__email")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "action", "target_table", "target_id", "created_at")
    list_filter = ("target_table",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("setting_key", "setting_value", "updated_at")
    search_fields = ("setting_key",)
