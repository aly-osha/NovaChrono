"""
Park the legacy cart-owned wishlist_items table before the wishlists app
creates the new one.

cart/0001_initial created `wishlist_items(buyer_id, product_id, added_at)`.
The schema moves wishlisting to its own app with a parent `wishlists` table
and a different `wishlist_items` shape (wishlist_id FK + added_price).

Renaming the legacy table to `wishlist_items_legacy` here keeps the data
available for wishlists/0002_migrate_legacy_wishlist_items to read, while
freeing the `wishlist_items` name for the new table. cart/0003 drops the
legacy table once the data has been copied.

Runs after cart/0001_initial (which created the table) and before the
wishlists app migrations (which create the new table).
"""

from django.db import migrations, models


def park_legacy_table(apps, schema_editor):
    """Rename legacy wishlist_items aside, dropping its indexes first.

    SQLite index names live in a single per-database namespace, so the
    renamed table's auto-generated indexes (wishlist_items_product_id_...)
    would collide with the indexes Django creates for the NEW wishlist_items
    table of the same name. Dropping them first frees those names.
    """
    with schema_editor.connection.cursor() as c:
        existing = set(schema_editor.connection.introspection.table_names())
        if "wishlist_items" in existing and "wishlist_items_legacy" not in existing:
            c.execute('ALTER TABLE "wishlist_items" RENAME TO "wishlist_items_legacy"')
        # Drop the legacy table's indexes (now named ..._legacy_... after the
        # rename, but drop by the pre-rename names too, defensively).
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name IN ('wishlist_items','wishlist_items_legacy') "
            "AND name NOT LIKE 'sqlite_%'"
        )
        for (idx,) in c.fetchall():
            c.execute(f'DROP INDEX IF EXISTS "{idx}"')


def unpark_legacy_table(apps, schema_editor):
    existing = set(schema_editor.connection.introspection.table_names())
    with schema_editor.connection.cursor() as c:
        if "wishlist_items_legacy" in existing and "wishlist_items" not in existing:
            c.execute('ALTER TABLE "wishlist_items_legacy" RENAME TO "wishlist_items"')


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(park_legacy_table, unpark_legacy_table),
    ]
