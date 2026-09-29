"""
analytics/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ActivityLog(models.Model):
    admin_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="activity_logs",
    )
    action = models.CharField(max_length=255)
    target_table = models.CharField(max_length=50, blank=True, default="")
    target_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.admin_user} — {self.action}"


class SystemSetting(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="system_settings_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"

    def __str__(self):
        return f"{self.setting_key} = {self.setting_value[:40]}"
