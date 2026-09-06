from catalog.models import TCG, Category
from orders.models import StoreSettings
from cart.models import Cart
from wishlist.models import Wishlist


def global_context(request):
    """
    Context processor that supplies global navigation data,
    cart items count, wishlist counter, and store settings.
    """
    cart_count = 0
    wishlist_count = 0

    # Cart resolution (Authenticated User vs Guest Session)
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = cart.item_count
        # Wishlist count for authenticated buyer
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_count = wishlist.item_count
    else:
        if request.session.session_key:
            cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if cart:
                cart_count = cart.item_count

    # Active TCG universes & Categories
    header_tcgs = TCG.objects.filter(is_active=True).order_by('display_order', 'name')
    header_categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
    store_settings = StoreSettings.get_settings()

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'header_tcgs': header_tcgs,
        'header_categories': header_categories,
        'store_settings': store_settings,
    }
