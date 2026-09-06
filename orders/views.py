import random
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Order, OrderItem, OrderStatusHistory, Payment, Invoice, InvoiceItem, StoreSettings
from .pdf import generate_invoice_pdf
from cart.models import Cart
from accounts.models import Address
from dashboard.models import ActivityLog


def generate_unique_order_number(prefix="NC-2026-"):
    """
    Generates a sequential or randomized unique order number.
    """
    while True:
        num = random.randint(100000, 999999)
        order_number = f"{prefix}{num}"
        if not Order.objects.filter(order_number=order_number).exists():
            return order_number


@login_required
def checkout_view(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty. Discover cards to begin checkout.")
        return redirect('cart:cart_detail')

    user_addresses = user.addresses.all()
    store_settings = StoreSettings.get_settings()

    if request.method == 'POST':
        # 1. Address resolution
        selected_address_id = request.POST.get('selected_address')
        if selected_address_id and selected_address_id != 'new':
            address_obj = get_object_or_404(Address, id=selected_address_id, user=user)
            shipping_name = address_obj.full_name
            shipping_phone = address_obj.phone
            shipping_addr1 = address_obj.address_line1
            shipping_addr2 = address_obj.address_line2
            shipping_city = address_obj.city
            shipping_state = address_obj.state
            shipping_postal = address_obj.postal_code
            shipping_country = address_obj.country
        else:
            shipping_name = request.POST.get('full_name', '').strip()
            shipping_phone = request.POST.get('phone', '').strip()
            shipping_addr1 = request.POST.get('address_line1', '').strip()
            shipping_addr2 = request.POST.get('address_line2', '').strip()
            shipping_city = request.POST.get('city', '').strip()
            shipping_state = request.POST.get('state', '').strip()
            shipping_postal = request.POST.get('postal_code', '').strip()
            shipping_country = request.POST.get('country', 'United States').strip()

            if not (shipping_name and shipping_phone and shipping_addr1 and shipping_city and shipping_state and shipping_postal):
                messages.error(request, "Please fill in all required shipping address fields.")
                return render(request, 'orders/checkout.html', {
                    'cart': cart,
                    'user_addresses': user_addresses,
                    'store_settings': store_settings
                })

            # Save address if requested
            if request.POST.get('save_address') == 'on':
                Address.objects.create(
                    user=user,
                    full_name=shipping_name,
                    phone=shipping_phone,
                    address_line1=shipping_addr1,
                    address_line2=shipping_addr2,
                    city=shipping_city,
                    state=shipping_state,
                    postal_code=shipping_postal,
                    country=shipping_country,
                    is_default_shipping=not user_addresses.exists()
                )

        # Payment details (Mock Gateway)
        payment_method = request.POST.get('payment_method', 'CREDIT_CARD')
        card_brand = request.POST.get('card_brand', 'Visa')
        card_last4 = request.POST.get('card_last4', '4242')[-4:]
        customer_notes = request.POST.get('customer_notes', '').strip()

        # Database Transaction: Atomically validate stock, create order, deduct inventory, generate invoice
        try:
            with transaction.atomic():
                # 1. Validate all items stock
                cart_items = list(cart.items.select_related('product', 'product__inventory').all())
                for item in cart_items:
                    product = item.product
                    if not product.is_preorder:
                        if hasattr(product, 'inventory'):
                            if product.inventory.stock_quantity < item.quantity and not product.inventory.allow_backorders:
                                raise ValueError(f"Insufficient stock for '{product.name}'. Only {product.inventory.stock_quantity} available.")

                # 2. Create Order
                order_number = generate_unique_order_number(prefix=store_settings.invoice_prefix)
                order = Order.objects.create(
                    order_number=order_number,
                    user=user,
                    status=Order.Status.CONFIRMED,
                    subtotal=cart.subtotal,
                    discount_amount=cart.discount_amount,
                    shipping_amount=cart.shipping_amount,
                    tax_amount=cart.tax_amount,
                    total_amount=cart.total,
                    coupon_code=cart.coupon.code if cart.coupon else '',
                    shipping_name=shipping_name,
                    shipping_phone=shipping_phone,
                    shipping_address_line1=shipping_addr1,
                    shipping_address_line2=shipping_addr2,
                    shipping_city=shipping_city,
                    shipping_state=shipping_state,
                    shipping_postal_code=shipping_postal,
                    shipping_country=shipping_country,
                    billing_name=shipping_name,
                    billing_address=f"{shipping_addr1}, {shipping_city}, {shipping_state} {shipping_postal}",
                    customer_notes=customer_notes,
                    carrier="NovaChrono Vault Express / DHL",
                )

                # 3. Create OrderItems and Deduct Inventory
                for item in cart_items:
                    product = item.product
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name_snapshot=product.name,
                        sku_snapshot=product.sku,
                        tcg_snapshot=product.tcg.name if product.tcg else '',
                        condition_snapshot=product.get_condition_display(),
                        unit_price=product.price,
                        quantity=item.quantity,
                        subtotal=item.line_total,
                    )

                    # Deduct inventory
                    if hasattr(product, 'inventory') and not product.is_preorder:
                        inv = product.inventory
                        inv.stock_quantity = max(0, inv.stock_quantity - item.quantity)
                        inv.save()

                # 4. Create Payment record
                payment_id = f"PAY-{order_number}"
                Payment.objects.create(
                    order=order,
                    payment_id=payment_id,
                    payment_method=payment_method,
                    amount=order.total_amount,
                    currency='USD',
                    status=Payment.Status.PAID,
                    transaction_reference=f"TXN-CHRONO-{random.randint(1000000, 9999999)}",
                    card_brand=card_brand,
                    card_last4=card_last4
                )

                # 5. Generate Invoice
                invoice = Invoice.objects.create(
                    invoice_number=order_number,  # Clean sequential format
                    order=order,
                    due_date=date.today() + timedelta(days=7),
                    subtotal=order.subtotal,
                    discount_amount=order.discount_amount,
                    shipping_amount=order.shipping_amount,
                    tax_amount=order.tax_amount,
                    grand_total=order.total_amount,
                    customer_name=shipping_name,
                    customer_email=user.email,
                    customer_phone=shipping_phone,
                    shipping_address=order.full_shipping_address,
                    billing_address=order.billing_address,
                    store_name=store_settings.store_name,
                    store_address=f"{store_settings.address_line1}, {store_settings.city}, {store_settings.state} {store_settings.postal_code}",
                    store_tax_id=store_settings.tax_id,
                    store_email=store_settings.email,
                    store_phone=store_settings.phone,
                )

                for item in order.items.all():
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product_name=item.product_name_snapshot,
                        sku=item.sku_snapshot,
                        tcg=item.tcg_snapshot,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.subtotal,
                    )

                # 6. Status History
                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status=Order.Status.PENDING,
                    new_status=Order.Status.CONFIRMED,
                    changed_by=user,
                    note="Order placed and payment authorized via NovaChrono Vault."
                )

                # 7. Clear Cart
                cart.items.all().delete()
                cart.coupon = None
                cart.save()

                # 8. Activity Log
                ActivityLog.log(
                    user=user,
                    action=f"Order Placed: #{order.order_number}",
                    details=f"Amount: ${order.total_amount:.2f} ({order.total_items} items)"
                )

            messages.success(request, "Order successfully placed and verified!")
            return redirect('orders:confirmation', order_number=order.order_number)

        except ValueError as err:
            messages.error(request, str(err))
            return redirect('cart:cart_detail')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred during checkout: {str(e)}")
            return redirect('cart:cart_detail')

    context = {
        'cart': cart,
        'user_addresses': user_addresses,
        'store_settings': store_settings,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_confirmation_view(request, order_number):
    order = get_object_or_404(Order.objects.select_related('payment', 'invoice').prefetch_related('items'), order_number=order_number)

    # Permission check: owner or staff
    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Order not found.")

    return render(request, 'orders/confirmation.html', {'order': order})


@login_required
def order_history_view(request):
    user = request.user
    status_filter = request.GET.get('status', 'all')
    search_q = request.GET.get('q', '').strip()

    orders = Order.objects.filter(user=user).select_related('payment', 'invoice').prefetch_related('items')

    if search_q:
        orders = orders.filter(order_number__icontains=search_q)

    if status_filter == 'active':
        orders = orders.filter(status__in=[Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PROCESSING, Order.Status.PACKED, Order.Status.SHIPPED])
    elif status_filter == 'delivered':
        orders = orders.filter(status=Order.Status.DELIVERED)
    elif status_filter == 'cancelled':
        orders = orders.filter(status=Order.Status.CANCELLED)

    return render(request, 'orders/history.html', {
        'orders': orders,
        'status_filter': status_filter,
        'search_q': search_q,
    })


@login_required
def order_detail_view(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related('payment', 'invoice').prefetch_related('items', 'status_history'),
        order_number=order_number
    )

    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Order not found.")

    # Timeline stage index mapping
    status_order = [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
        Order.Status.PACKED,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    ]
    try:
        current_step_index = status_order.index(order.status)
    except ValueError:
        current_step_index = -1  # Cancelled

    return render(request, 'orders/detail.html', {
        'order': order,
        'current_step_index': current_step_index,
        'status_order': status_order,
    })


@login_required
@require_POST
def cancel_order_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Permission denied.")

    if not order.can_cancel:
        messages.error(request, "This order has already progressed past the cancellable fulfillment stage.")
        return redirect('orders:detail', order_number=order.order_number)

    reason = request.POST.get('reason', 'Buyer requested cancellation.').strip()

    with transaction.atomic():
        prev_status = order.status
        order.status = Order.Status.CANCELLED
        order.cancellation_reason = reason
        order.cancelled_by = request.user
        order.cancelled_at = timezone.now()
        order.save()

        # Restore inventory
        for item in order.items.all():
            if item.product and hasattr(item.product, 'inventory'):
                inv = item.product.inventory
                inv.stock_quantity += item.quantity
                inv.save()

        # Record status change
        OrderStatusHistory.objects.create(
            order=order,
            previous_status=prev_status,
            new_status=Order.Status.CANCELLED,
            changed_by=request.user,
            note=f"Cancelled: {reason}"
        )

        ActivityLog.log(
            user=request.user,
            action=f"Order Cancelled: #{order.order_number}",
            details=f"Reason: {reason}"
        )

    messages.info(request, f"Order #{order.order_number} has been cancelled and inventory restored.")
    return redirect('orders:detail', order_number=order.order_number)


@login_required
def invoice_detail_view(request, order_number):
    """
    Printable A4 HTML Invoice with @media print styling.
    """
    order = get_object_or_404(Order.objects.select_related('invoice', 'payment').prefetch_related('invoice__items'), order_number=order_number)

    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Invoice not accessible.")

    invoice = getattr(order, 'invoice', None)
    if not invoice:
        raise Http404("Invoice has not been generated for this order.")

    return render(request, 'orders/invoice_print.html', {'invoice': invoice, 'order': order})


@login_required
def invoice_pdf_view(request, order_number):
    """
    Downloadable A4 PDF Invoice generated via ReportLab.
    """
    order = get_object_or_404(Order.objects.select_related('invoice', 'payment').prefetch_related('invoice__items'), order_number=order_number)

    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Invoice not accessible.")

    invoice = getattr(order, 'invoice', None)
    if not invoice:
        raise Http404("Invoice not found.")

    pdf_bytes = generate_invoice_pdf(invoice)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"NovaChrono_Invoice_{invoice.invoice_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def packing_slip_view(request, order_number):
    """
    Printable warehouse packing slip (checklist, SKU, items, delivery instructions).
    """
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number)

    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Packing slip not accessible.")

    store_settings = StoreSettings.get_settings()
    return render(request, 'orders/packing_slip.html', {'order': order, 'store_settings': store_settings})


@login_required
def shipping_label_view(request, order_number):
    """
    Printable carrier shipping label layout.
    """
    order = get_object_or_404(Order, order_number=order_number)

    if order.user != request.user and not request.user.is_staff_member:
        raise Http404("Shipping label not accessible.")

    store_settings = StoreSettings.get_settings()
    return render(request, 'orders/shipping_label.html', {'order': order, 'store_settings': store_settings})
