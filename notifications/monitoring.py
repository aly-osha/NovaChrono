"""
notifications/monitoring.py — the engine behind FR-21 .. FR-25.

Schema rule 10 removes the price_alerts / restock_alerts tables: wishlist
membership IS the subscription. This module walks the wishlist and raises a
Notification when a watched product actually changes in a way the buyer
asked to hear about:

  FR-21  adding to the wishlist starts monitoring   (WishlistItem row)
  FR-22  notify when the price decreases           (price_drop event)
  FR-23  notify when an unavailable item returns   (restock event)
  FR-24  removing from the wishlist stops it       (row is deleted)
  FR-25  surface those events in-app              (notifications page)

Dedup is the subtle part. A monitor that naively compares "current price <
added_price" would re-notify on every sweep for as long as the price stayed
low. Instead each event is recorded once per distinct state change:

  price_drop -> fires when price falls below the last price we REPORTED
                for that item (tracked by event_price)
  restock    -> fires when an item that was unavailable becomes available,
                tracked by whether a restock notification already exists
                for the current in-stock state

run_monitoring() is safe to call as often as you like.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Notification
from wishlists.models import WishlistItem


def _fmt(amount):
    """Format a price the way the storefront does (rupees, 2dp)."""
    return f"₹{amount:,.2f}"


@transaction.atomic
def check_wishlist_item(item):
    """Evaluate one WishlistItem; create Notifications for new events.

    Returns the list of Notifications created (possibly empty).
    """
    product = item.product
    created = []

    # ---- FR-22: price decrease -------------------------------------------
    # Compare against the price we last *reported*, not the price at watch
    # time. If the buyer was told about ₹500 already, staying at ₹500 must
    # not notify again; dropping to ₹400 must.
    current = product.price
    last_reported = item.added_price

    if last_reported is not None and current < last_reported:
        already_told = Notification.objects.filter(
            buyer=item.wishlist.buyer,
            product=product,
            notification_type="price_drop",
            event_price=current,
        ).exists()
        if not already_told:
            saved = current - last_reported
            pct = (saved / last_reported * Decimal("100")) if last_reported else Decimal("0")
            n = Notification.objects.create(
                buyer=item.wishlist.buyer,
                product=product,
                notification_type="price_drop",
                title=f"Price drop: {product.name}",
                message=(
                    f"{product.name} dropped from {_fmt(last_reported)} to "
                    f"{_fmt(current)} — a saving of {_fmt(saved)} "
                    f"({pct:.1f}%)."
                ),
                event_price=current,
            )
            created.append(n)

    # ---- FR-23: back in stock -------------------------------------------
    # Only fires when the item is actually purchasable AND was previously out of stock.
    if product.is_available:
        if item.was_out_of_stock:
            n = Notification.objects.create(
                buyer=item.wishlist.buyer,
                product=product,
                notification_type="restock",
                title=f"Back in stock: {product.name}",
                message=(
                    f"{product.name} is available again at {_fmt(current)} "
                    f"({product.stock} in stock)."
                ),
                event_price=current,
            )
            created.append(n)
            item.was_out_of_stock = False
            item.save(update_fields=["was_out_of_stock"])
    else:
        if not item.was_out_of_stock:
            item.was_out_of_stock = True
            item.save(update_fields=["was_out_of_stock"])

    # Advance the reported-price baseline so the same drop cannot re-fire.
    if last_reported is None or current < last_reported:
        item.added_price = current
        item.save(update_fields=["added_price"])

    return created


def run_monitoring():
    """Sweep every wishlist item. Returns (items_checked, notifications_created)."""
    items = (
        WishlistItem.objects
        .select_related("product", "wishlist", "wishlist__buyer")
        .iterator()
    )
    checked = 0
    created = []
    for item in items:
        checked += 1
        created.extend(check_wishlist_item(item))
    return checked, created


def unread_count(user):
    """Badge count for the nav bell."""
    return user.notifications.filter(is_read=False).count()


def mark_all_read(user):
    """POST action: clear the unread badge."""
    return user.notifications.filter(is_read=False).update(is_read=True)