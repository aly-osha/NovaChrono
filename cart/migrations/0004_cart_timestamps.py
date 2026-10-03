"""
Close compliance gap G-2 (schema §10): carts.created_at / carts.updated_at.

The schema requires timestamps on `carts`; every other documented table has
them, but Cart was missed during the 20-table alignment. Adding the columns
to a populated table needs a one-off default, so it is supplied here rather
than interactively.

Written by hand because `auto_now_add` cannot be added to an existing table
without a default, and `makemigrations --noinput` refuses rather than guess.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0003_drop_legacy_wishlist_items"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="cart",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]