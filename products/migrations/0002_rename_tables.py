"""
Step 1 of the products schema alignment: physical table renames.

  products            -> catalog_items
  product_images      -> catalog_item_images
  single_card_details -> single_cards

This runs as its own migration, BEFORE any column operations, because a
single migration cannot both rename a table and then AlterField on it —
Django's schema editor resolves the physical table name from the migration
state, so a later AlterField in the same migration would still target the
old table name and fail.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        # AlterModelTable emits the physical `ALTER TABLE ... RENAME TO ...`
        # and updates migration state in one step. It must run before any
        # AlterField in a later migration, because the schema editor
        # resolves physical table names from migration state.
        migrations.AlterModelTable(name="product", table="catalog_items"),
        migrations.AlterModelTable(
            name="productimage", table="catalog_item_images"
        ),
        migrations.AlterModelTable(
            name="singlecarddetail", table="single_cards"
        ),
    ]
