from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import Cart, CartItem
from catalog.models import Product, Promotion


def get_or_create_cart(request):
    """
    Retrieves or creates an active cart for authenticated user or guest session.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    if not request.session.session_key:
        request.session.create()

    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def cart_detail_view(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product', 'product__tcg', 'product__inventory').all()
    free_shipping_remaining = max(Decimal('0.00'), Decimal('150.00') - cart.subtotal)

    context = {
        'cart': cart,
        'items': items,
        'free_shipping_remaining': free_shipping_remaining,
    }
    return render(request, 'cart/cart.html', context)


@require_POST
def add_to_cart_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        quantity = 1

    # Check stock
    current_stock = product.current_stock
    if not product.is_preorder and current_stock < quantity and not (hasattr(product, 'inventory') and product.inventory.allow_backorders):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': f"Only {current_stock} items left in stock!"}, status=400)
        messages.error(request, f"Cannot add {quantity} items. Only {current_stock} units left in stock.")
        return redirect('catalog:product_detail', slug=product.slug)

    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        new_qty = cart_item.quantity + quantity
        if not product.is_preorder and current_stock < new_qty and not (hasattr(product, 'inventory') and product.inventory.allow_backorders):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f"Cannot add more. Limit of {current_stock} reached."}, status=400)
            messages.warning(request, f"Only {current_stock} available in stock.")
            return redirect('cart:cart_detail')
        cart_item.quantity = new_qty
        cart_item.save()
    else:
        cart_item.quantity = quantity
        cart_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f"✓ Added {product.name} to your vault cart",
            'cart_count': cart.item_count,
            'subtotal': f"${cart.subtotal:.2f}",
        })

    messages.success(request, f"Added '{product.name}' to your cart.")
    return redirect('cart:cart_detail')


@require_POST
def update_cart_quantity_view(request, item_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    action = request.POST.get('action')
    qty = request.POST.get('quantity')

    if action == 'increment':
        cart_item.quantity += 1
    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            cart_item = None
    elif qty is not None:
        try:
            qty_val = int(qty)
            if qty_val <= 0:
                cart_item.delete()
                cart_item = None
            else:
                cart_item.quantity = qty_val
        except ValueError:
            pass

    if cart_item:
        # Check stock limits
        current_stock = cart_item.product.current_stock
        if not cart_item.product.is_preorder and current_stock < cart_item.quantity and not (hasattr(cart_item.product, 'inventory') and cart_item.product.inventory.allow_backorders):
            cart_item.quantity = max(1, current_stock)
        cart_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.item_count,
            'item_quantity': cart_item.quantity if cart_item else 0,
            'line_total': f"${cart_item.line_total:.2f}" if cart_item else "$0.00",
            'subtotal': f"${cart.subtotal:.2f}",
            'discount': f"-${cart.discount_amount:.2f}",
            'shipping': f"${cart.shipping_amount:.2f}" if cart.shipping_amount > 0 else "FREE",
            'tax': f"${cart.tax_amount:.2f}",
            'total': f"${cart.total:.2f}",
            'item_removed': cart_item is None,
        })

    return redirect('cart:cart_detail')


@require_POST
def remove_from_cart_view(request, item_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item_name = cart_item.product.name
    cart_item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f"Removed {item_name} from cart",
            'cart_count': cart.item_count,
            'subtotal': f"${cart.subtotal:.2f}",
            'discount': f"-${cart.discount_amount:.2f}",
            'shipping': f"${cart.shipping_amount:.2f}" if cart.shipping_amount > 0 else "FREE",
            'tax': f"${cart.tax_amount:.2f}",
            'total': f"${cart.total:.2f}",
        })

    messages.info(request, f"Removed {item_name} from your cart.")
    return redirect('cart:cart_detail')


@require_POST
def apply_coupon_view(request):
    cart = get_or_create_cart(request)
    code = request.POST.get('coupon_code', '').strip().upper()

    promotion = Promotion.objects.filter(code=code, is_active=True).first()
    if not promotion:
        messages.error(request, "Invalid or expired promotional voucher code.")
        return redirect('cart:cart_detail')

    if cart.subtotal < promotion.minimum_spend:
        messages.error(request, f"Voucher '{code}' requires a minimum spend of ${promotion.minimum_spend:.2f}.")
        return redirect('cart:cart_detail')

    cart.coupon = promotion
    cart.save()
    messages.success(request, f"Voucher code '{code}' successfully applied!")
    return redirect('cart:cart_detail')


@require_POST
def remove_coupon_view(request):
    cart = get_or_create_cart(request)
    cart.coupon = None
    cart.save()
    messages.info(request, "Promotional code removed.")
    return redirect('cart:cart_detail')
