"""
Backfill data required by the schema alignment.

(catalog_items.game_id and category_id are backfilled inside
products/0003_schema_alignment, since that is where the NOT NULL columns
are introduced. This migration handles the derived columns that other apps
added.)

1. orders.shipping_* snapshot (schema rule 9) from the linked address.
2. order_items.subtotal is derived (unit_price * quantity).
3. reviews.status is derived from the legacy is_approved flag.
4. authenticity_certificates.certificate_number / issue_date are derived.
"""

from django.db import migrations
from django.utils import timezone


def forwards(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")
    Review = apps.get_model("reviews", "Review")
    Cert = apps.get_model("certificates", "AuthenticityCertificate")

    # --- 1: immutable shipping snapshot on orders ---
    for o in Order.objects.select_related("shipping_address", "buyer").all():
        if o.shipping_address_line1:
            continue
        addr = o.shipping_address
        buyer = o.buyer
        o.shipping_name = getattr(buyer, "name", "") or ""
        o.shipping_address_line1 = addr.line1
        o.shipping_address_line2 = addr.line2
        o.shipping_city = addr.city
        o.shipping_state = addr.state
        o.shipping_postal_code = addr.postal_code
        o.shipping_country = addr.country
        o.save(
            update_fields=[
                "shipping_name", "shipping_address_line1", "shipping_address_line2",
                "shipping_city", "shipping_state", "shipping_postal_code",
                "shipping_country",
            ]
        )

    # --- 2: derived order_items.subtotal ---
    for oi in OrderItem.objects.all():
        oi.subtotal = oi.unit_price * oi.quantity
        oi.save(update_fields=["subtotal"])

    # --- 3: reviews.status from is_approved ---
    for r in Review.objects.all():
        r.status = "approved" if r.is_approved else "pending"
        r.save(update_fields=["status"])

    # --- 4: certificate_number / issue_date ---
    for c in Cert.objects.all():
        changed = False
        if not c.certificate_number:
            c.certificate_number = f"NC-{c.verification_code}"
            changed = True
        if c.issue_date is None:
            c.issue_date = (c.issued_at or timezone.now()).date()
            changed = True
        if changed:
            c.save(update_fields=["certificate_number", "issue_date"])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("certificates", "0002_schema_alignment"),
        ("orders", "0002_schema_alignment"),
        ("products", "0003_schema_alignment"),
        ("reviews", "0002_schema_alignment"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
