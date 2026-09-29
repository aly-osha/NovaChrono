"""
cart/views.py — cart only. Wishlist views moved to wishlists/views.py
to match the schema's separate wishlists / wishlist_items tables.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Cart, CartItem
from products.models import Product


@login_required
def cart(request):
    cart, _ = Cart.objects.get_or_create(buyer=request.user)
    items = cart.items.select_related("product").all()
    return render(request, "cart/cart.html", {
        "cart": cart,
        "items": items,
    })


@login_required
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not product.is_available:
        messages.error(request, f"{product.name} is out of stock.")
        return redirect("product_detail", pk=pk)

    try:
        qty = max(1, int(request.GET.get("qty", 1)))
    except (ValueError, TypeError):
        qty = 1
    qty = min(qty, product.stock)

    cart, _ = Cart.objects.get_or_create(buyer=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity = min(item.quantity + qty, product.stock)
        item.save()
    else:
        item.quantity = qty
        item.save()
    messages.success(request, f"Added {qty}× {product.name} to cart.")
    return redirect("cart")


@login_required
def cart_update(request, pk):
    cart = Cart.objects.get(buyer=request.user)
    item = get_object_or_404(cart.items, product_id=pk)
    qty = int(request.POST.get("quantity", 1))
    if qty < 1:
        item.delete()
    else:
        item.quantity = qty
        item.save()
    return redirect("cart")


@login_required
def cart_remove(request, pk):
    cart = Cart.objects.get(buyer=request.user)
    cart.items.filter(product_id=pk).delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart")


# NOTE: wishlist, wishlist_to_cart and remove_from_wishlist now live in
# wishlists/views.py — the schema gives wishlisting its own two tables.
