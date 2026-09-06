from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Wishlist, WishlistItem
from catalog.models import Product


def wishlist_view(request):
    if not request.user.is_authenticated:
        messages.info(request, "Sign in to NovaChrono to access your personal collection wishlist.")
        return render(request, 'wishlist/wishlist.html', {'is_guest': True})

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    items = wishlist.items.select_related('product', 'product__tcg', 'product__category', 'product__inventory').all()

    return render(request, 'wishlist/wishlist.html', {
        'wishlist': wishlist,
        'items': items,
        'is_guest': False,
    })


@require_POST
def toggle_wishlist_view(request, product_id):
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'login_required': True,
                'message': 'Please sign in to add items to your wishlist.',
                'login_url': f'/accounts/login/?next=/product/{Product.objects.get(id=product_id).slug}/'
            })
        messages.info(request, "Please log in to save items to your wishlist.")
        return redirect('accounts:login')

    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    existing = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()

    if existing:
        existing.delete()
        is_in_wishlist = False
        msg = f"Removed {product.name} from your wishlist."
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        is_in_wishlist = True
        msg = f"Saved {product.name} to your wishlist."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_in_wishlist': is_in_wishlist,
            'wishlist_count': wishlist.item_count,
            'message': msg
        })

    messages.success(request, msg)
    return redirect('wishlist:wishlist')


@require_POST
def remove_from_wishlist_view(request, item_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    name = item.product.name
    item.delete()
    messages.info(request, f"Removed '{name}' from your wishlist.")
    return redirect('wishlist:wishlist')
