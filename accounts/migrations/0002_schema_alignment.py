"""
Align accounts schema with NovaChrono_Database_Schema.

users:
  + status (ACTIVE/INACTIVE/SUSPENDED), created_at, updated_at
  is_active stays (Django auth requires it) and is kept in sync in
  User.save().

addresses:
  line1  -> db_column address_line1   (schema rule naming)
  line2  -> db_column address_line2
  + created_at, updated_at
  + partial unique index: one default address per user (schema rule 1)

Python attributes are unchanged (`line1`, `line2`, `buyer`) so all existing
forms, views and templates keep working.
"""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # ---- users ----
        migrations.AddField(
            model_name="user",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                    ("suspended", "Suspended"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),

        # ---- addresses ----
        migrations.AlterField(
            model_name="address",
            name="line1",
            field=models.CharField(
                db_column="address_line1", max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="address",
            name="line2",
            field=models.CharField(
                blank=True, db_column="address_line2", default="", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="address",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="address",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True)),
                fields=("buyer",),
                name="uniq_default_address_per_user",
            ),
        ),
    ]
