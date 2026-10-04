"""
products/views.py — catalogue browsing, search, filtering, product detail.
Wishlist/alert views moved to wishlists/views.py (schema: separate
wishlists + wishlist_items tables; no price_alerts table).
"""
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Product, Game, Set, Category, SingleCardDetail, ProductImage

PAGINATE_BY = 12


def home(request):
    featured = Product.objects.filter(is_active=True).order_by("-created_at")[:8]
    return render(request, "home.html", {"featured": featured})


def catalogue(request):
    qs = Product.objects.filter(is_active=True).select_related(
        "set", "game", "category", "set__game", "single_card"
    ).prefetch_related("images")

    # keyword search
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    # game filter — the schema gives catalog_items a direct game_id
    game_ids = request.GET.getlist("game")
    if game_ids:
        qs = qs.filter(game_id__in=game_ids)

    # category filter
    cat_ids = request.GET.getlist("category")
    if cat_ids:
        qs = qs.filter(category_id__in=cat_ids)

    # product type tabs: Single Cards vs Sealed Products
    ptype = request.GET.get("type", "single_card").strip()
    if ptype not in ["single_card", "sealed", "related"]:
        ptype = "single_card"
    qs = qs.filter(product_type=ptype)

    # rarity (single cards)
    rarity = request.GET.get("rarity", "").strip()
    if rarity:
        qs = qs.filter(single_card__rarity__icontains=rarity)

    # language
    lang = request.GET.get("language", "").strip()
    if lang:
        qs = qs.filter(single_card__language__icontains=lang)

    # condition
    condition = request.GET.get("condition", "").strip()
    if condition:
        qs = qs.filter(single_card__condition=condition)

    # price range — coerce defensively.
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    price_filter_error = None

    def _to_decimal(raw):
        if not raw:
            return None
        try:
            value = Decimal(raw)
            return value if value >= 0 else False
        except (InvalidOperation, ValueError, TypeError):
            return False

    min_dec = _to_decimal(min_price)
    max_dec = _to_decimal(max_price)
    if min_dec is False or max_dec is False:
        price_filter_error = "Enter a valid non-negative price."
    else:
        if min_dec is not None:
            qs = qs.filter(price__gte=min_dec)
        if max_dec is not None:
            qs = qs.filter(price__lte=max_dec)

    # availability
    avail = request.GET.get("available", "").strip()
    if avail == "1":
        qs = qs.filter(stock__gt=0)

    # annotate avg rating for approved reviews only
    qs = qs.annotate(annotated_rating=Avg("reviews__rating", filter=Q(reviews__is_approved=True)))

    # ordering
    sort = request.GET.get("sort", "name")
    if sort == "price_asc":
        qs = qs.order_by("price", "name")
    elif sort == "price_desc":
        qs = qs.order_by("-price", "name")
    elif sort == "rating":
        qs = qs.order_by("-annotated_rating", "-created_at")
    else:
        qs = qs.order_by("name")

    # Tab counts (for active items)
    single_cards_count = Product.objects.filter(is_active=True, product_type="single_card").count()
    sealed_count = Product.objects.filter(is_active=True, product_type="sealed").count()

    # Active filters count for filter icon badge
    active_filters_count = 0
    if game_ids:
        active_filters_count += len(game_ids)
    if cat_ids:
        active_filters_count += len(cat_ids)
    if rarity:
        active_filters_count += 1
    if lang:
        active_filters_count += 1
    if condition:
        active_filters_count += 1
    if min_dec is not None or max_dec is not None:
        active_filters_count += 1
    if avail == "1":
        active_filters_count += 1

    # sidebar & filter data
    games = Game.objects.all()
    categories = Category.objects.filter(is_active=True)

    paginator = Paginator(qs, PAGINATE_BY)
    page = request.GET.get("page", 1)
    products = paginator.get_page(page)

    # build a copy of cleaned query params for pagination links
    params = request.GET.copy()
    if "page" in params:
        del params["page"]

    return render(request, "products/catalogue.html", {
        "products": products,
        "games": games,
        "categories": categories,
        "query_params": params,
        "page_obj": products,
        "price_filter_error": price_filter_error,
        "current_type": ptype,
        "single_cards_count": single_cards_count,
        "sealed_count": sealed_count,
        "active_filters_count": active_filters_count,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related(
        "set", "game", "category"
    ).prefetch_related("images", "reviews"), pk=pk, is_active=True)
    images = product.images.all()
    reviews = product.reviews.filter(is_approved=True).select_related("buyer")
    related = Product.objects.filter(
        set=product.set, is_active=True
    ).exclude(pk=pk)[:4]
    # Monitoring state derives from wishlist membership (schema rule 10).
    user_alert = None
    in_wishlist = False
    if request.user.is_authenticated:
        from wishlists.models import WishlistItem
        user_alert = WishlistItem.objects.filter(
            wishlist__buyer=request.user, product=product,
        ).first()
        in_wishlist = user_alert is not None
    return render(request, "products/detail.html", {
        "product": product,
        "images": images,
        "reviews": reviews,
        "related": related,
        "user_alert": user_alert,
        "in_wishlist": in_wishlist,
    })


def verify_certificate(request):
    from certificates.views import public_verify
    return public_verify(request)


def api_sets(request):
    """Dynamic sets endpoint for game selector."""
    game_id = request.GET.get("game")
    sets = Set.objects.filter(is_active=True)
    if game_id:
        sets = sets.filter(game_id=game_id)
    sets = sets.select_related("game")
    data = [
        {"pk": s.pk, "name": s.name, "game_name": s.game.name}
        for s in sets
    ]
    return JsonResponse(data, safe=False)


@login_required
def price_alert_create(request, pk):
    """Deprecated shim — see wishlists.views.price_alert_create."""
    from wishlists.views import price_alert_create as _impl
    return _impl(request, pk)


@login_required
def add_to_wishlist(request, pk):
    """Deprecated shim — see wishlists.views.add_to_wishlist."""
    from wishlists.views import add_to_wishlist as _impl
    return _impl(request, pk)


@login_required
def remove_from_wishlist(request, pk):
    """Deprecated shim — see wishlists.views.remove_from_wishlist."""
    from wishlists.views import remove_from_wishlist as _impl
    return _impl(request, pk)
