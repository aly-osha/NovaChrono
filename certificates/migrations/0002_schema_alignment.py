"""
Align certificates with NovaChrono_Database_Schema (table 18).

  + certificate_number (UNIQUE), issue_date, status, created_at, updated_at
  verification_code widened to VARCHAR(100) per the schema.

qr_code_url, issued_by, issued_at and is_active are retained because
FR-50..FR-58 (generation, QR representation, public verification,
revocation) depend on them. status and is_active are kept in sync in save().
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("certificates", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="authenticitycertificate",
            name="certificate_number",
            field=models.CharField(blank=True, default="", max_length=100, unique=True),
        ),
        migrations.AddField(
            model_name="authenticitycertificate",
            name="issue_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="authenticitycertificate",
            name="status",
            field=models.CharField(
                choices=[
                    ("valid", "Valid"),
                    ("revoked", "Revoked"),
                    ("expired", "Expired"),
                ],
                default="valid",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="authenticitycertificate",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
        ),
        migrations.AddField(
            model_name="authenticitycertificate",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="authenticitycertificate",
            name="verification_code",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterModelOptions(
            name="authenticitycertificate",
            options={
                "ordering": ["-issued_at"],
                "db_table": "authenticity_certificates",
            },
        ),
    ]
