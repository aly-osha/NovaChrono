"""
orders/views.py
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone

from .pdf import generate_invoice_pdf

from .models import (
    Order, OrderItem, Payment, STATUS_CHOICES,
    PAYMENT_METHOD_CHOICES, CASH_ON_DELIVERY,
)
from cart.models import Cart
from accounts.models import Address
from analytics.models import ActivityLog
from products.models import Product


@login_required
def checkout(request):
    cart = Cart.objects.filter(buyer=request.user).first()
    if cart is None or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    # verify stock initially
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
    # a payment form that cannot succeed.
    if not addresses and request.method == "POST":
        messages.error(
            request,
            "Add a delivery address before placing your order.",
        )
        return redirect("address_create")

    if request.method == "POST":
        address_id = request.POST.get("address")
        payment_method = request.POST.get("payment_method", "card")

        valid_methods = {value for value, _ in PAYMENT_METHOD_CHOICES}
        if payment_method not in valid_methods:
            messages.error(request, "Please choose a valid payment method.")
            return redirect("checkout")

        if not address_id:
            messages.error(request, "Please select a shipping address.")
            return redirect("checkout")

        address = get_object_or_404(request.user.addresses, pk=address_id)

        with transaction.atomic():
            # Concurrency protection: lock rows for products in cart
            cart_items = list(cart.items.select_related("product"))
            product_ids = [item.product_id for item in cart_items]
            locked_products = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }

            # Re-verify stock with locked records
            for item in cart_items:
                locked_prod = locked_products.get(item.product_id)
                if not locked_prod or locked_prod.stock < item.quantity:
                    messages.error(
                        request,
                        f"{item.product.name} is no longer available in the requested quantity.",
                    )
                    return redirect("cart")

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

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                    subtotal=item.product.price * item.quantity,
                )
                # decrement stock on locked instance
                locked_prod = locked_products[item.product_id]
                locked_prod.stock -= item.quantity
                locked_prod.save(update_fields=["stock", "updated_at"])
                if locked_prod.stock == 0:
                    from wishlists.models import WishlistItem
                    WishlistItem.objects.filter(product=locked_prod).update(was_out_of_stock=True)

            # COD is collected at the door: the order is confirmed but the
            # payment stays pending until the buyer pays on delivery.
            is_cod = payment_method == CASH_ON_DELIVERY
            payment = Payment.objects.create(
                order=order,
                method=payment_method,
                amount=total,
                status="pending" if is_cod else "success",
                transaction_ref=(
                    f"COD-{order.pk}" if is_cod else f"SANDBOX-{order.pk}"
                ),
                paid_at=None if is_cod else timezone.now(),
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
    orders = (
        request.user.orders
        .select_related("shipping_address")
        .prefetch_related("items__product")
        .all()
    )
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        request.user.orders
        .select_related("shipping_address", "payment")
        .prefetch_related("items__product__images"),
        pk=pk,
    )
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_invoice_pdf(request, pk):
    """Generate and download official PDF tax invoice for an order.

    Accessible to the buyer who placed the order and administrative staff.
    """
    if _is_admin(request.user):
        order_qs = Order.objects.all()
    else:
        order_qs = request.user.orders.all()

    order = get_object_or_404(
        order_qs
        .select_related("buyer", "shipping_address", "payment")
        .prefetch_related("items__product__game", "items__product__set", "items__product__single_card"),
        pk=pk,
    )

    pdf_bytes = generate_invoice_pdf(order)
    disposition = "inline" if request.GET.get("view") == "inline" else "attachment"
    filename = f"Invoice-NC-{order.pk:05d}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response


# ---- Admin order views ----

def _is_admin(user):
    return user.is_authenticated and user.role in ("admin", "super_admin")


@login_required
@user_passes_test(_is_admin)
def admin_order_list(request):
    """Admin view of all orders."""
    orders = (
        Order.objects
        .select_related("buyer", "shipping_address")
        .annotate(item_count=Count("items"))
        .prefetch_related("items__product")
        .all()
    )
    return render(request, "orders/admin_order_list.html", {"orders": orders})


@login_required
@user_passes_test(_is_admin)
def admin_order_detail(request, pk):
    order = get_object_or_404(
        Order.objects
        .select_related("buyer", "shipping_address", "payment")
        .prefetch_related("items__product__images"),
        pk=pk,
    )

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in [s[0] for s in STATUS_CHOICES]:
            old = order.status
            order.status = new_status
            order.save()

            # If COD order was delivered, mark payment success
            if (
                new_status == "delivered"
                and hasattr(order, "payment")
                and order.payment.status == "pending"
                and order.payment.method == CASH_ON_DELIVERY
            ):
                order.payment.status = "success"
                order.payment.paid_at = timezone.now()
                order.payment.save(update_fields=["status", "paid_at", "updated_at"])

            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Order #{order.pk} status: {old} → {new_status}",
                target_table="orders",
                target_id=order.pk,
            )
            messages.success(request, f"Status updated to {new_status}.")

    return render(request, "orders/admin_order_detail.html", {
        "order": order,
        "statuses": STATUS_CHOICES,
    })
