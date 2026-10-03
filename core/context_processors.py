"""
core/context_processors.py — inject brand + cart stats into every template.
"""
from django.db.models import Sum

from products.models import Product
from cart.models import Cart


def branding(request):
    return {
        "BRAND": {
            "name": "NovaChrono",
            "tagline": "Collect · Verify · Discover",
            "colors": {
                "primary": "#7928CA",
                "secondary": "#00E5FF",
                "tertiary": "#D4AF37",
                "surface": "#121317",
                "on_surface": "#E3E2E8",
            },
        },
    }


def cart_stats(request):
    """Return cart item count + unread notification count for the nav badges."""
    cart_count = 0
    unread_notifications = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(buyer=request.user)
            cart_count = cart.items.aggregate(total=Sum("quantity"))["total"] or 0
        except Cart.DoesNotExist:
            cart_count = 0
        # FR-25: unread badge for the in-app notifications centre.
        unread_notifications = request.user.notifications.filter(
            is_read=False
        ).count()
    return {
        "CART_COUNT": cart_count,
        "NOTIFICATION_UNREAD": unread_notifications,
    }
