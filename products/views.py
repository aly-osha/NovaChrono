"""
products/views.py
"""
from django.db.models import Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from .models import Product, Game, Set, Category, SingleCardDetail, ProductImage

PAGINATE_BY = 12


def home(request):
    featured = Product.objects.filter(is_active=True).order_by("-created_at")[:8]
    return render(request, "home.html", {"featured": featured})


def catalogue(request):
    qs = Product.objects.filter(is_active=True).select_related("set", "set__game")

    # keyword search
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    # game filter
    game_ids = request.GET.getlist("game")
    if game_ids:
        qs = qs.filter(set__game_id__in=game_ids)

    # category filter
    cat_ids = request.GET.getlist("category")
    if cat_ids:
        qs = qs.filter(category_id__in=cat_ids)

    # product type
    ptype = request.GET.get("type", "").strip()
    if ptype:
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

    # price range
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    if min_price:
        qs = qs.filter(price__gte=min_price)
    if max_price:
        qs = qs.filter(price__lte=max_price)

    # availability
    avail = request.GET.get("available", "").strip()
    if avail == "1":
        qs = qs.filter(stock__gt=0)

    # annotate avg rating (named to avoid clashing with Product.avg_rating property)
    qs = qs.annotate(annotated_rating=Avg("reviews__rating"))

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

    # sidebar data
    games = Game.objects.all()
    categories = Category.objects.filter(is_active=True, parent__isnull=True)

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
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related(
        "set", "set__game", "category"
    ).prefetch_related("images", "reviews"), pk=pk, is_active=True)
    images = product.images.all()
    reviews = product.reviews.filter(is_approved=True).select_related("buyer")
    related = Product.objects.filter(
        set=product.set, is_active=True
    ).exclude(pk=pk)[:4]
    user_alert = None
    if request.user.is_authenticated:
        from .models import PriceAlert
        user_alert = PriceAlert.objects.filter(
            buyer=request.user, product=product, is_active=True,
        ).first()
    return render(request, "products/detail.html", {
        "product": product,
        "images": images,
        "reviews": reviews,
        "related": related,
        "user_alert": user_alert,
    })


def verify_certificate(request):
    from certificates.models import AuthenticityCertificate
    code = request.GET.get("code", "").strip().upper()
    cert = None
    found = False
    if code:
        try:
            cert = AuthenticityCertificate.objects.get(
                verification_code=code, is_active=True,
            )
            found = True
        except AuthenticityCertificate.DoesNotExist:
            found = False
    # public page — render with or without cert
    return render(request, "certificates/verify.html", {
        "code": code,
        "cert": cert,
        "found": found,
    })


@login_required
def price_alert_create(request, pk):
    """Save a price-drop watch for a product (FR-21/22)."""
    from decimal import Decimal, InvalidOperation
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if request.method == "POST":
        try:
            target = Decimal(request.POST.get("target_price", "").strip())
            if target <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError, AttributeError):
            messages.error(request, "Enter a valid target price.")
            return redirect("product_detail", pk=pk)
        from .models import PriceAlert
        PriceAlert.objects.update_or_create(
            buyer=request.user, product=product,
            defaults={"target_price": target, "is_active": True},
        )
        messages.success(
            request,
            f"Price alert active — we'll notify you when {product.name} "
            f"drops to ₹{target}.",
        )
    return redirect("product_detail", pk=pk)


@login_required
def add_to_wishlist(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    request.user.wishlist.update_or_create(
        product=product,
        defaults={"buyer": request.user},
    )
    messages.success(request, f"{product.name} added to wishlist.")
    return redirect("product_detail", pk=pk)


@login_required
def remove_from_wishlist(request, pk):
    product = get_object_or_404(Product, pk=pk)
    request.user.wishlist.filter(product=product).delete()
    messages.success(request, "Removed from wishlist.")
    return redirect("wishlist")
