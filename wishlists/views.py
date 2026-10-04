"""
wishlists/views.py — wishlist + price/restock monitoring (FR-17..FR-25).

The schema has no price_alerts or restock_alerts table (rule 10): a buyer
watching a product is simply a WishlistItem, and the events monitoring
produces are Notifications. That is what this module implements.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cart.models import Cart, CartItem
from products.models import Product

from .models import Wishlist, WishlistItem


def _wishlist_for(user):
    """Get or create the buyer's single wishlist."""
    wishlist, _ = Wishlist.objects.get_or_create(buyer=user)
    return wishlist


@login_required
def wishlist(request):
    wl = _wishlist_for(request.user)
    items = (
        wl.items
        .select_related("product", "product__game", "product__set", "product__set__game")
        .prefetch_related("product__images")
        .all()
    )
    # Monitoring state is derived, not stored (schema rule 10).
    price_drops = [i for i in items if i.is_price_drop]
    return render(request, "cart/wishlist.html", {
        "items": items,
        "wishlist": wl,
        "price_drops": price_drops,
    })


@login_required
def add_to_wishlist(request, pk):
    """Wishlisting a product activates price-drop + restock monitoring."""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    wl = _wishlist_for(request.user)
    item, created = WishlistItem.objects.get_or_create(
        wishlist=wl,
        product=product,
        defaults={
            "added_price": product.price,
            "was_out_of_stock": not product.is_available,
        },
    )
    if not created and item.added_price != product.price:
        # Re-watching resets the baseline the drop is measured against.
        item.added_price = product.price
        item.save()
    messages.success(
        request,
        f"{product.name} added to wishlist — we'll notify you on a price "
        f"drop or when it's back in stock.",
    )
    return redirect("product_detail", pk=pk)


@login_required
def remove_from_wishlist(request, pk):
    """Removing from the wishlist also disables monitoring (FR-24)."""
    product = get_object_or_404(Product, pk=pk)
    WishlistItem.objects.filter(
        wishlist__buyer=request.user, product=product
    ).delete()
    messages.success(request, "Removed from wishlist.")
    return redirect("wishlist")


@login_required
def wishlist_to_cart(request, pk):
    item = get_object_or_404(
        WishlistItem.objects.select_related("product"),
        wishlist__buyer=request.user,
        product_id=pk,
    )
    product = item.product
    if not product.is_available:
        messages.error(request, f"{product.name} is currently out of stock.")
        return redirect("wishlist")

    cart, _ = Cart.objects.get_or_create(buyer=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity = min(cart_item.quantity + 1, product.stock)
        cart_item.save(update_fields=["quantity"])
    item.delete()
    messages.success(request, f"Moved {product.name} to cart.")
    return redirect("cart")


@login_required
def price_alert_create(request, pk):
    """Legacy route (detail page "Watch Price" button).

    The schema removed the price_alerts table, so setting a price alert now
    means joining the wishlist — which is what activates monitoring. The
    posted target price is recorded as the watch baseline.
    """
    from decimal import Decimal, InvalidOperation

    product = get_object_or_404(Product, pk=pk, is_active=True)
    if request.method == "POST":
        wl = _wishlist_for(request.user)
        target = None
        try:
            raw = request.POST.get("target_price", "").strip()
            if raw:
                parsed = Decimal(raw)
                if parsed > 0:
                    target = parsed
        except (InvalidOperation, ValueError, AttributeError):
            target = None

        WishlistItem.objects.update_or_create(
            wishlist=wl,
            product=product,
            defaults={
                "added_price": target or product.price,
                "was_out_of_stock": not product.is_available,
            },
        )
        if target:
            messages.success(
                request,
                f"Watching {product.name} — we'll notify you if it drops "
                f"to ₹{target} or comes back in stock.",
            )
        else:
            messages.success(
                request,
                f"{product.name} added to your wishlist — price-drop and "
                f"restock alerts are now active.",
            )
    return redirect("product_detail", pk=pk)


@login_required
def check_monitoring_now(request):
    """Run the sweep on demand (FR-21..FR-23).

    In production this belongs on a cron (`manage.py check_monitoring`); this
    POST endpoint lets an admin (or a manual test) trigger it without shell
    access. Cheap enough to run per request for a small catalogue, but it is
    a full table walk — hence POST-only and admin-gated.
    """
    from notifications.monitoring import run_monitoring

    if not request.user.is_admin_role:
        messages.error(request, "Admin access required.")
        return redirect("home")

    checked, created = run_monitoring()
    messages.success(
        request,
        f"Monitoring checked {checked} wishlist item(s) and created "
        f"{len(created)} notification(s).",
    )
    return redirect("notification_list")
