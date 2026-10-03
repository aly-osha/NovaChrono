"""
orders/views.py
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum

from .models import (
    Order, OrderItem, Payment, STATUS_CHOICES,
    PAYMENT_METHOD_CHOICES, CASH_ON_DELIVERY,
)
from cart.models import Cart
from accounts.models import Address
from analytics.models import ActivityLog


@login_required
def checkout(request):
    cart = Cart.objects.filter(buyer=request.user).first()
    if cart is None or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    # verify stock
    for item in cart.items.select_related("product"):
        if item.product.stock < item.quantity:
            messages.error(
                request,
                f"{item.product.name} has insufficient stock "
                f"(available: {item.product.stock}).",
            )
            return redirect("cart")

    addresses = list(request.user.addresses.all())

    # No saved address: show the page with an explanation instead of rendering
    # a payment form that cannot succeed. Previously this fell through to the
    # POST branch, found no address, and redirected back to /checkout/ with a
    # flash the user could miss — orders looked like they silently failed.
    if not addresses and request.method == "POST":
        messages.error(
            request,
            "Add a delivery address before placing your order.",
        )
        return redirect("address_create")

    if request.method == "POST":
        address_id = request.POST.get("address")
        payment_method = request.POST.get("payment_method", "card")

        # Reject a method the model does not accept instead of letting it
        # through to the DB layer, where it raises and 500s the request.
        valid_methods = {value for value, _ in PAYMENT_METHOD_CHOICES}
        if payment_method not in valid_methods:
            messages.error(request, "Please choose a valid payment method.")
            return redirect("checkout")

        if not address_id:
            messages.error(request, "Please select a shipping address.")
            return redirect("checkout")

        address = get_object_or_404(request.user.addresses, pk=address_id)

        with transaction.atomic():
            total = cart.subtotal

            order = Order.objects.create(
                buyer=request.user,
                shipping_address=address,
                total_amount=total,
            )
            # schema rule 9: freeze the address onto the order at checkout so
            # later edits to the saved address cannot rewrite order history.
            order.shipping_name = (
                address.buyer.get_full_name() or address.buyer.email
            )
            order.shipping_address_line1 = address.line1
            order.shipping_address_line2 = address.line2
            order.shipping_city = address.city
            order.shipping_state = address.state
            order.shipping_postal_code = address.postal_code
            order.shipping_country = address.country
            order.save()

            for item in cart.items.select_related("product"):
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                    subtotal=item.product.price * item.quantity,
                )
                # decrement stock
                item.product.stock -= item.quantity
                item.product.save()

            # COD is collected at the door: the order is confirmed but the
            # payment stays pending until the buyer pays on delivery. Every
            # other method settles immediately in this mock implementation.
            is_cod = payment_method == CASH_ON_DELIVERY
            payment = Payment.objects.create(
                order=order,
                method=payment_method,
                status="pending" if is_cod else "success",
                transaction_ref=(
                    f"COD-{order.pk}" if is_cod else f"SANDBOX-{order.pk}"
                ),
                paid_at=None if is_cod else order.created_at,
            )

            # clear cart
            cart.items.all().delete()

            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Order placed: #{order.pk}",
                target_table="orders",
                target_id=order.pk,
            )

        if is_cod:
            messages.success(
                request,
                f"Order #{order.pk} confirmed! Pay ₹{order.total_amount} "
                "cash on delivery.",
            )
        else:
            messages.success(
                request,
                f"Order #{order.pk} confirmed! Total: ₹{order.total_amount}",
            )
        return redirect("order_detail", pk=order.pk)

    return render(request, "orders/checkout.html", {
        "cart": cart,
        "addresses": addresses,
    })


@login_required
def order_list(request):
    orders = request.user.orders.select_related("shipping_address").all()
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        request.user.orders.select_related("payment").prefetch_related("items__product"),
        pk=pk,
    )
    return render(request, "orders/order_detail.html", {"order": order})


# ---- Admin order views ----

def _is_admin(user):
    """Admin gate for the order views.

    Previously admin_order_list defined a local is_admin() and never applied
    it, so /admin/orders/ rendered every customer's order — address, phone and
    all — to anonymous visitors. The check existed but was dead code.
    """
    return user.is_authenticated and user.role in ("admin", "super_admin")


@login_required
@user_passes_test(_is_admin)
def admin_order_list(request):
    """Admin view of all orders."""
    orders = Order.objects.select_related(
        "buyer", "shipping_address"
    ).prefetch_related("items__product").all()
    return render(request, "orders/admin_order_list.html", {"orders": orders})


@login_required
@user_passes_test(_is_admin)
def admin_order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("buyer", "shipping_address", "payment")
        .prefetch_related("items__product"),
        pk=pk,
    )

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in [s[0] for s in STATUS_CHOICES]:
            from analytics.models import ActivityLog
            old = order.status
            order.status = new_status
            order.save()
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Order #{order.pk} status: {old} → {new_status}",
                target_table="orders",
                target_id=order.pk,
            )
            messages.success(request, f"Status updated to {new_status}.")

    return render(request, "orders/admin_order_detail.html", {"order": order})
