"""
Align analytics with NovaChrono_Database_Schema (table 20).

  target_table -> db_column entity_type
  target_id    -> db_column entity_id
  + description, timestamps, index on (entity_type, entity_id)
  + action narrowed to VARCHAR(100) per the schema.

SystemSetting is intentionally NOT dropped — it is not one of the 20 tables,
but FR-75 requires Admin to manage system-wide configuration and
/admin/settings/ is a live page. See the note in analytics/models.py.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activitylog",
            name="target_table",
            field=models.CharField(
                blank=True, db_column="entity_type", default="", max_length=50
            ),
        ),
        migrations.AlterField(
            model_name="activitylog",
            name="target_id",
            field=models.IntegerField(blank=True, db_column="entity_id", null=True),
        ),
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="systemsetting",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
        ),
    ]
