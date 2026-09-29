from django.shortcuts import render
from products.models import Product, Game


def home(request):
    """NovaChrono homepage — hero, trust bar, game explorer, trending products."""
    featured = Product.objects.filter(is_active=True).order_by("-created_at")[:8]
    games = Game.objects.all()
    # Hero mosaic: two random single cards flanking a center grail (Stitch hero).
    singles = list(
        Product.objects.filter(is_active=True, product_type="single_card")
        .select_related("set", "game")
        .order_by("?")[:2]
    )
    hero_left = singles[0] if len(singles) > 0 else None
    hero_right = singles[1] if len(singles) > 1 else None
    hero_center = (
        Product.objects.filter(is_active=True, product_type="sealed")
        .select_related("set", "game")
        .order_by("-created_at")
        .first()
    ) or (featured[0] if featured else None)
    return render(request, "home.html", {
        "featured": featured,
        "games": games,
        "hero_left": hero_left,
        "hero_right": hero_right,
        "hero_center": hero_center,
    })
