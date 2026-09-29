"""
orders/views.py
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum

from .models import Order, OrderItem, Payment, STATUS_CHOICES
from cart.models import Cart
from accounts.models import Address
from analytics.models import ActivityLog


@login_required
def checkout(request):
    cart = Cart.objects.get(buyer=request.user)
    if not cart.items.exists():
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

    addresses = request.user.addresses.filter(is_active=True) if hasattr(Address, 'is_active') else request.user.addresses.all()
    if request.method == "POST":
        address_id = request.POST.get("address")
        payment_method = request.POST.get("payment_method", "sandbox")

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

            for item in cart.items.select_related("product"):
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                )
                # decrement stock
                item.product.stock -= item.quantity
                item.product.save()

            payment = Payment.objects.create(
                order=order,
                method=payment_method,
                status="success",  # sandbox always succeeds
                transaction_ref=f"SANDBOX-{order.pk}",
                paid_at=order.created_at,
            )

            # clear cart
            cart.items.all().delete()

            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Order placed: #{order.pk}",
                target_table="orders",
                target_id=order.pk,
            )

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

def admin_order_list(request):
    """Admin view of all orders."""
    from django.contrib.auth.decorators import user_passes_test
    from django.contrib.auth import get_user_model

    def is_admin(user):
        return user.is_authenticated and user.role in ("admin", "super_admin")

    orders = Order.objects.select_related(
        "buyer", "shipping_address"
    ).prefetch_related("items__product").all()
    return render(request, "orders/admin_order_list.html", {"orders": orders})


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
