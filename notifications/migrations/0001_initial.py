"""
New notifications app — schema table 19.

Notifications are the delivery mechanism for wishlist-activated monitoring
(FR-22 price drop, FR-23 restock, FR-25 in-app notifications). The schema
has no price_alerts / restock_alerts table (rule 10).
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("price_drop", "Price drop"),
                            ("restock", "Back in stock"),
                            ("order_update", "Order update"),
                            ("review", "Review activity"),
                            ("system", "System"),
                        ],
                        default="system",
                        max_length=30,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "notifications",
                "ordering": ["-created_at"],
            },
        ),
    ]
