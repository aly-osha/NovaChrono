"""
New wishlists app — schema tables 12 and 13.

The schema splits wishlisting into a parent (wishlists, one per user) and a
child (wishlist_items). added_price records the price at watch time so
price-drop monitoring has a baseline without a price_alerts table
(schema rule 10).
"""

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # The park step renames the legacy cart-owned wishlist_items table so
        # this migration can create a clean one with the new shape.
        ("cart", "0002a_park_legacy_wishlist_items"),
        ("products", "0003_schema_alignment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Wishlist",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "buyer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wishlist_record",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "wishlists"},
        ),
        migrations.CreateModel(
            name="WishlistItem",
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
                ("added_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wishlist_items",
                        to="products.product",
                    ),
                ),
                (
                    "wishlist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="wishlists.wishlist",
                    ),
                ),
            ],
            options={
                "db_table": "wishlist_items",
                "ordering": ["-added_at"],
                "unique_together": {("wishlist", "product")},
            },
        ),
    ]
