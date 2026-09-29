"""
Align products schema with NovaChrono_Database_Schema.

  products            -> catalog_items        (table rename)
  product_images      -> catalog_item_images  (table rename)
  single_card_details -> single_cards         (table rename)
  sealed_packs        -> new one-to-one marker table

Also adds the schema's description/is_active/timestamp columns to games,
sets and categories, flattens categories (drops the self-FK `parent`),
and gives catalog_items a direct NOT NULL game FK plus stock_quantity.

The Python model names are unchanged (Product, ProductImage,
SingleCardDetail, `stock`, `sort_order`); only the physical schema moves.
"""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def backfill_product_taxonomy(apps, schema_editor):
    """Fill catalog_items.game_id from set.game (schema requires NOT NULL)."""
    Product = apps.get_model("products", "Product")
    Set = apps.get_model("products", "Set")
    Game = apps.get_model("products", "Game")

    game_by_set = {s.pk: s.game_id for s in Set.objects.all()}
    default_game = Game.objects.order_by("pk").first()
    if default_game is None:
        return  # nothing to infer from

    for p in Product.objects.filter(game__isnull=True):
        game_id = game_by_set.get(p.set_id) or default_game.pk
        p.game_id = game_id
        p.save(update_fields=["game"])


def backfill_product_categories(apps, schema_editor):
    """Fill catalog_items.category_id (schema requires NOT NULL)."""
    Product = apps.get_model("products", "Product")
    Category = apps.get_model("products", "Category")

    default_cat = Category.objects.order_by("pk").first()
    if default_cat is None:
        return

    for p in Product.objects.filter(category__isnull=True):
        p.category_id = default_cat.pk
        p.save(update_fields=["category"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_rename_tables"),
    ]

    operations = [
        # ---- games: description / is_active / timestamps ----
        migrations.AddField(
            model_name="game",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="game",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="game",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="game",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="game",
            options={
                "ordering": ["name"],
                "verbose_name_plural": "Games",
            },
        ),

        # ---- sets: code / release_date / description / is_active / timestamps ----
        migrations.AddField(
            model_name="set",
            name="code",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="set",
            name="release_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="set",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="set",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="set",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="set",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="set", options={"ordering": ["name"]}
        ),

        # ---- categories: flat (drop parent), add description/timestamps ----
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="category",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="category", options={"ordering": ["name"]}
        ),
        migrations.RemoveField(model_name="category", name="parent"),

        # ---- catalog_items: stock -> stock_quantity column, NOT NULL category + game ----
        # The model keeps the attribute `stock` with db_column="stock_quantity",
        # so the field name in migration state must stay `stock`.
        migrations.AlterField(
            model_name="product",
            name="stock",
            field=models.IntegerField(
                db_column="stock_quantity",
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        # game / category become NOT NULL per the schema, but the tables are
        # populated, so: add nullable -> backfill -> tighten.
        migrations.AddField(
            model_name="product",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="products.game",
                null=True,
            ),
        ),
        migrations.RunPython(backfill_product_taxonomy, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="products.game",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="products.category",
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_product_categories, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="products.category",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="product",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterModelOptions(
            name="product", options={"ordering": ["name"]}
        ),
        # ---- single_cards: card_number, wider rarity/condition ----
        migrations.AddField(
            model_name="singlecarddetail",
            name="card_number",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AlterField(
            model_name="singlecarddetail",
            name="rarity",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="singlecarddetail",
            name="condition",
            field=models.CharField(
                blank=True,
                default="",
                max_length=50,
                choices=[
                    ("near_mint", "Near Mint"),
                    ("lightly_played", "Lightly Played"),
                    ("moderately_played", "Moderately Played"),
                    ("heavily_played", "Heavily Played"),
                    ("damaged", "Damaged"),
                ],
            ),
        ),

        # ---- catalog_item_images: sort_order -> display_order column ----
        # Model keeps attribute `sort_order` with db_column="display_order".
        migrations.AlterField(
            model_name="productimage",
            name="sort_order",
            field=models.IntegerField(db_column="display_order", default=0),
        ),

        # ---- sealed_packs (new table) ----
        migrations.CreateModel(
            name="SealedPack",
            fields=[
                (
                    "product",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="sealed_pack",
                        serialize=False,
                        to="products.product",
                    ),
                ),
            ],
            options={"db_table": "sealed_packs"},
        ),

        # ---- price_alerts removed (schema rule 10) ----
        # NOTE: no DeleteModel needed. The legacy products/0002_pricealert
        # migration that created the PriceAlert model was removed from the
        # tree during this restructure, so PriceAlert is not in the migration
        # state at all. The physical price_alerts table (if present from a
        # previous migrate) is dropped here.
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "price_alerts";',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
