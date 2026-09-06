from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from decimal import Decimal
from .models import Product, TCG, Category, Review


def home_view(request):
    """
    Editorial homepage inspired by Fable and modern luxury collectible culture.
    """
    # Active TCG Universes
    tcgs = TCG.objects.filter(is_active=True).order_by('display_order')[:6]

    # Featured Chase Cards & Products
    featured_products = Product.objects.filter(
        is_active=True, is_featured=True
    ).select_related('tcg', 'category').prefetch_related('images')[:8]

    # New Arrivals
    new_arrivals = Product.objects.filter(
        is_active=True
    ).select_related('tcg', 'category').prefetch_related('images').order_by('-created_at')[:8]

    # Pre-orders
    preorders = Product.objects.filter(
        is_active=True, is_preorder=True
    ).select_related('tcg', 'category').prefetch_related('images')[:6]

    # Collector's Picks (High-value or graded/exclusive items)
    collectors_picks = Product.objects.filter(
        is_active=True
    ).select_related('tcg', 'category').prefetch_related('images').order_by('-price')[:4]

    # Accessories
    accessories = Product.objects.filter(
        is_active=True,
        category__slug__in=['accessories', 'sleeves', 'deck-boxes', 'binders', 'playmats']
    ).select_related('tcg', 'category').prefetch_related('images')[:4]

    # Categories
    categories = Category.objects.filter(is_active=True).order_by('display_order')[:8]

    context = {
        'tcgs': tcgs,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'preorders': preorders,
        'collectors_picks': collectors_picks,
        'accessories': accessories,
        'categories': categories,
    }
    return render(request, 'catalog/home.html', context)


def shop_view(request, category_slug=None, tcg_slug=None):
    """
    Comprehensive product catalog with multi-filtering, sorting, and pagination.
    """
    products = Product.objects.filter(is_active=True).select_related('tcg', 'category', 'inventory').prefetch_related('images')

    # Selected entities
    selected_tcg = None
    selected_category = None

    if tcg_slug:
        selected_tcg = get_object_or_404(TCG, slug=tcg_slug, is_active=True)
        products = products.filter(tcg=selected_tcg)

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=selected_category)

    # Query params filters
    tcg_param = request.GET.get('tcg')
    if tcg_param and not selected_tcg:
        products = products.filter(tcg__slug=tcg_param)
        selected_tcg = TCG.objects.filter(slug=tcg_param).first()

    category_param = request.GET.get('category')
    if category_param and not selected_category:
        products = products.filter(category__slug=category_param)
        selected_category = Category.objects.filter(slug=category_param).first()

    product_type_param = request.GET.get('product_type')
    if product_type_param:
        products = products.filter(product_type=product_type_param)

    condition_param = request.GET.get('condition')
    if condition_param:
        products = products.filter(condition=condition_param)

    stock_param = request.GET.get('stock')
    if stock_param == 'in_stock':
        products = products.filter(Q(inventory__stock_quantity__gt=0) | Q(is_preorder=True))
    elif stock_param == 'preorder':
        products = products.filter(is_preorder=True)

    # Price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (ValueError, ArithmeticError):
            pass
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (ValueError, ArithmeticError):
            pass

    # Search keyword
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(sku__icontains=query) |
            Q(tcg__name__icontains=query) |
            Q(category__name__icontains=query)
        )

    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'best_selling':
        products = products.order_by('-is_featured', '-created_at')
    else:  # featured
        products = products.order_by('-is_featured', '-is_new', '-created_at')

    # Pagination: 12 per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    all_tcgs = TCG.objects.filter(is_active=True).order_by('name')
    all_categories = Category.objects.filter(is_active=True).order_by('name')
    product_types = Product.ProductType.choices
    conditions = Product.Condition.choices

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'all_tcgs': all_tcgs,
        'all_categories': all_categories,
        'product_types': product_types,
        'conditions': conditions,
        'selected_tcg': selected_tcg,
        'selected_category': selected_category,
        'selected_type': product_type_param,
        'selected_condition': condition_param,
        'selected_stock': stock_param,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'query': query,
        'sort_by': sort_by,
        'total_count': paginator.count,
    }
    return render(request, 'catalog/shop.html', context)


def product_detail_view(request, slug):
    """
    High-end product detail view with image gallery, specs, authenticity guarantee,
    and related items.
    """
    product = get_object_or_404(
        Product.objects.select_related('tcg', 'category', 'inventory').prefetch_related('images'),
        slug=slug,
        is_active=True
    )

    related_products = Product.objects.filter(
        Q(tcg=product.tcg) | Q(category=product.category),
        is_active=True
    ).exclude(id=product.id).select_related('tcg', 'category').prefetch_related('images')[:4]

    reviews = product.reviews.filter(is_approved=True)

    # In-wishlist check for authenticated buyer
    is_in_wishlist = False
    if request.user.is_authenticated and hasattr(request.user, 'wishlist'):
        is_in_wishlist = request.user.wishlist.items.filter(product=product).exists()

    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'is_in_wishlist': is_in_wishlist,
    }
    return render(request, 'catalog/product_detail.html', context)


def quick_view_api(request, product_id):
    """
    JSON API for quick-view modal preview on hover or click.
    """
    product = get_object_or_404(
        Product.objects.select_related('tcg', 'category', 'inventory').prefetch_related('images'),
        id=product_id,
        is_active=True
    )

    images = [img.get_image_url() for img in product.images.all()]
    if not images:
        images = [product.primary_image]

    data = {
        'id': product.id,
        'name': product.name,
        'slug': product.slug,
        'tcg': product.tcg.name,
        'category': product.category.name,
        'price': f"{product.price:.2f}",
        'compare_at_price': f"{product.compare_at_price:.2f}" if product.compare_at_price else None,
        'discount_percentage': product.discount_percentage,
        'short_description': product.short_description or product.description[:180] + '...',
        'condition': product.get_condition_display(),
        'edition': product.edition,
        'language': product.get_language_display(),
        'stock_status': product.stock_status,
        'is_in_stock': product.is_in_stock,
        'is_preorder': product.is_preorder,
        'primary_image': product.primary_image,
        'images': images,
        'detail_url': f"/product/{product.slug}/",
    }
    return JsonResponse(data)


def search_suggest_api(request):
    """
    Live autocomplete search suggestions.
    """
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(tcg__name__icontains=query) |
        Q(category__name__icontains=query),
        is_active=True
    ).select_related('tcg', 'category')[:6]

    results = []
    for p in products:
        results.append({
            'id': p.id,
            'name': p.name,
            'tcg': p.tcg.name,
            'category': p.category.name,
            'price': f"${p.price:.2f}",
            'image': p.primary_image,
            'url': f"/product/{p.slug}/",
        })

    return JsonResponse({'results': results})


def search_view(request):
    """
    Direct search view rendering the shop template with the query parameter.
    """
    return shop_view(request)
