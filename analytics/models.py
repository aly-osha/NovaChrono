"""
analytics/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ActivityLog(models.Model):
    """Schema table: activity_logs.

    The schema columns are entity_type and entity_id; the Python attributes
    stay target_table and target_id so existing admin views and templates
    keep working, via db_column mapping.
    """
    admin_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="activity_logs",
    )
    action = models.CharField(max_length=100)
    target_table = models.CharField(
        max_length=50, blank=True, default="", db_column="entity_type",
    )
    target_id = models.IntegerField(
        null=True, blank=True, db_column="entity_id",
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_table", "target_id"]),
        ]

    def __str__(self):
        return f"{self.admin_user} — {self.action}"

    @property
    def user(self):
        """Schema column is user_id."""
        return self.admin_user

    @property
    def entity_type(self):
        """Schema column name."""
        return self.target_table

    @property
    def entity_id(self):
        """Schema column name."""
        return self.target_id


class SystemSetting(models.Model):
    """Key/value store for system-wide configuration (FR-75).

    NOTE: this table is NOT one of the 20 tables in the database schema
    document. It is retained deliberately because FR-75 requires Admin to
    "manage system-wide configuration" and /admin/settings/ is a live page
    that reads and writes it. Removing it would break that requirement.
    """
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="system_settings_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"

    def __str__(self):
        return f"{self.setting_key} = {self.setting_value[:40]}"
