"""
Carry existing wishlist_items rows into the new wishlists / wishlist_items
pair, reading from the parked legacy table.

Before: cart-owned wishlist_items(buyer_id, product_id, added_at)
After:  wishlists(buyer_id) + wishlist_items(wishlist_id, product_id,
        added_at, added_price)

cart/0002a_park_legacy_wishlist_items renames the legacy table to
wishlist_items_legacy so the wishlists app can create a clean
wishlist_items. This migration copies the rows across, then
cart/0003_drop_legacy_wishlist_items removes the parked table.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    Wishlist = apps.get_model("wishlists", "Wishlist")
    NewItem = apps.get_model("wishlists", "WishlistItem")
    Product = apps.get_model("products", "Product")

    prices = {p.pk: p.price for p in Product.objects.all()}

    # Read the legacy table directly via SQL — it is not in migration state
    # (cart/0001_initial no longer creates WishlistItem).
    existing = set(schema_editor.connection.introspection.table_names())
    if "wishlist_items_legacy" not in existing:
        return

    with schema_editor.connection.cursor() as c:
        c.execute("SELECT buyer_id, product_id, added_at FROM wishlist_items_legacy")
        rows = c.fetchall()

    buyers = {}
    for buyer_id, product_id, added_at in rows:
        wl = buyers.get(buyer_id)
        if wl is None:
            wl, _ = Wishlist.objects.get_or_create(buyer_id=buyer_id)
            buyers[buyer_id] = wl
        NewItem.objects.get_or_create(
            wishlist_id=wl.pk,
            product_id=product_id,
            defaults={
                "added_at": added_at,
                "added_price": prices.get(product_id),
            },
        )


def backwards(apps, schema_editor):
    # The legacy table is preserved until cart/0003 drops it, so no action.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0002a_park_legacy_wishlist_items"),
        ("products", "0003_schema_alignment"),
        ("wishlists", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
