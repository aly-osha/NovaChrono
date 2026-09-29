"""
Remove the parked legacy wishlist_items_legacy table.

By the time this runs, wishlists/0002_migrate_legacy_wishlist_items has
copied every row into the new wishlists / wishlist_items pair, so the
legacy table is no longer needed.
"""

from django.db import migrations, models


def drop_parked_table(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute("DROP TABLE IF EXISTS wishlist_items_legacy")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0002a_park_legacy_wishlist_items"),
        ("wishlists", "0002_migrate_legacy_wishlist_items"),
    ]

    operations = [
        migrations.RunPython(drop_parked_table, noop),
    ]
