"""
Align reviews with NovaChrono_Database_Schema (table 17).

  comment   -> db_column review_text   (schema naming)
  + status (PENDING/APPROVED/REJECTED), updated_at
  + UNIQUE(buyer, product) — one review per buyer per item (schema rule 7)
  + rating validated 1-5 (schema rule 8)

`is_approved` is retained because templates and views filter on it, and
Review.save() keeps it in sync with `status`.
"""

import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="comment",
            field=models.TextField(blank=True, db_column="review_text", default=""),
        ),
        migrations.AddField(
            model_name="review",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="review",
            name="rating",
            field=models.SmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ]
            ),
        ),
        migrations.AlterUniqueTogether(
            name="review", unique_together={("buyer", "product")}
        ),
    ]
