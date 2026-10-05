"""
wishlists/views.py — wishlist + price/restock monitoring (FR-17..FR-25).

The schema has no price_alerts or restock_alerts table (rule 10): a buyer
watching a product is simply a WishlistItem, and the events monitoring
produces are Notifications. That is what this module implements.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse

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
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", "")

    existing = WishlistItem.objects.filter(wishlist=wl, product=product).first()
    if request.GET.get("toggle") == "1" and existing:
        existing.delete()
        in_wishlist = False
        msg = f"Removed {product.name} from wishlist."
    else:
        item, created = WishlistItem.objects.get_or_create(
            wishlist=wl,
            product=product,
            defaults={
                "added_price": product.price,
                "was_out_of_stock": not product.is_available,
            },
        )
        if not created and item.added_price != product.price:
            item.added_price = product.price
            item.save()
        in_wishlist = True
        msg = f"Added {product.name} to wishlist."

    if is_ajax:
        return JsonResponse({
            "status": "success",
            "message": msg,
            "in_wishlist": in_wishlist,
            "product_id": product.pk,
            "product_name": product.name,
        })

    messages.success(request, msg)
    fallback = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("product_detail", args=[pk])
    return redirect(fallback)


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
