"""
products/admin_views.py — product/category/set management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.utils import timezone

from .models import Product, Game, Set, Category, SingleCardDetail, ProductImage
from analytics.models import ActivityLog


def _is_admin(user):
    return user.is_authenticated and user.role in ("admin", "super_admin")


def admin_required(view_func):
    return user_passes_test(_is_admin)(view_func)


# ---- Games ----


@admin_required
def admin_game_list(request):
    games = Game.objects.all()
    return render(request, "admin/game_list.html", {"games": games})


@admin_required
def admin_game_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name and not Game.objects.filter(name__iexact=name).exists():
            Game.objects.create(name=name)
            messages.success(request, f"Game '{name}' created.")
            return redirect("admin_game_list")
        elif name:
            messages.error(request, "A game with this name already exists.")
    return render(request, "admin/game_form.html", {"title": "Add Game"})


@admin_required
def admin_game_edit(request, pk):
    game = get_object_or_404(Game, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name and not Game.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            game.name = name
            game.save()
            messages.success(request, f"Game updated to '{name}'.")
            return redirect("admin_game_list")
        messages.error(request, "Name already exists or invalid.")
    return render(request, "admin/game_form.html", {"title": "Edit Game", "game": game})


@admin_required
def admin_game_delete(request, pk):
    game = get_object_or_404(Game, pk=pk)
    game.delete()
    messages.success(request, f"Game '{game.name}' deleted.")
    return redirect("admin_game_list")


# ---- Sets ----


@admin_required
def admin_set_list(request):
    sets = Set.objects.select_related("game").all()
    games = Game.objects.all()
    return render(request, "admin/set_list.html", {"sets": sets, "games": games})


@admin_required
def admin_set_create(request):
    games = Game.objects.all()
    if request.method == "POST":
        game_id = request.POST.get("game")
        name = request.POST.get("name", "").strip()
        if game_id and name:
            Set.objects.create(game_id=game_id, name=name)
            messages.success(request, "Set created.")
            return redirect("admin_set_list")
    return render(request, "admin/set_form.html", {"games": games, "title": "Add Set"})


@admin_required
def admin_set_edit(request, pk):
    s = get_object_or_404(Set, pk=pk)
    games = Game.objects.all()
    if request.method == "POST":
        game_id = request.POST.get("game")
        name = request.POST.get("name", "").strip()
        if game_id and name:
            s.game_id = game_id
            s.name = name
            s.save()
            messages.success(request, "Set updated.")
            return redirect("admin_set_list")
    return render(request, "admin/set_form.html", {"games": games, "title": "Edit Set", "set": s})


@admin_required
def admin_set_delete(request, pk):
    s = get_object_or_404(Set, pk=pk)
    s.delete()
    messages.success(request, f"Set '{s.name}' deleted.")
    return redirect("admin_set_list")


# ---- Categories ----


@admin_required
def admin_category_list(request):
    cats = Category.objects.all()
    return render(request, "admin/category_list.html", {"categories": cats})


@admin_required
def admin_category_create(request):
    # Categories are flat in the schema (no self-FK parent column).
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        if name:
            Category.objects.create(name=name, description=description)
            messages.success(request, f"Category '{name}' created.")
            return redirect("admin_category_list")
    return render(request, "admin/category_form.html", {"parents": [], "title": "Add Category"})


@admin_required
def admin_category_edit(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        if name:
            cat.name = name
            cat.description = description
            cat.save()
            messages.success(request, f"Category updated to '{name}'.")
            return redirect("admin_category_list")
    return render(request, "admin/category_form.html", {"parents": [], "title": "Edit Category", "category": cat})


@admin_required
def admin_category_toggle(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    cat.is_active = not cat.is_active
    cat.save()
    return redirect("admin_category_list")


# ---- Products ----


@admin_required
def admin_product_list(request):
    qs = Product.objects.select_related("set", "game", "category").all()
    ptype = request.GET.get("type", "")
    game = request.GET.get("game", "")
    if ptype:
        qs = qs.filter(product_type=ptype)
    if game:
        qs = qs.filter(game_id=game)
    return render(request, "admin/product_list.html", {
        "products": qs,
        "games": Game.objects.all(),
    })


@admin_required
def admin_product_create(request):
    games = Game.objects.all()
    sets = Set.objects.select_related("game").all()
    categories = Category.objects.filter(is_active=True).all()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "")
        price = request.POST.get("price", "0")
        stock = request.POST.get("stock", "0")
        product_type = request.POST.get("product_type", "sealed")
        game_id = request.POST.get("game")
        set_id = request.POST.get("set")
        category_id = request.POST.get("category")

        if not name or not price:
            messages.error(request, "Name and price are required.")
            return render(request, "admin/product_form.html", {
                "games": games, "sets": sets, "categories": categories,
                "title": "Add Product",
            })

        with transaction.atomic():
            product = Product.objects.create(
                name=name,
                description=description,
                price=price,
                stock=stock,
                product_type=product_type,
                set_id=set_id or None,
                category_id=category_id or None,
            )

            if product_type == "single_card":
                SingleCardDetail.objects.create(
                    product=product,
                    rarity=request.POST.get("rarity", ""),
                    language=request.POST.get("language", ""),
                    condition=request.POST.get("condition", ""),
                )

            # images
            for img in request.FILES.getlist("images"):
                ProductImage.objects.create(product=product, image=img)

        ActivityLog.objects.create(
            admin_user=request.user,
            action=f"Product created: {name}",
            target_table="products",
            target_id=product.pk,
        )
        messages.success(request, f"Product '{name}' created.")
        return redirect("admin_product_list")

    return render(request, "admin/product_form.html", {
        "games": games, "sets": sets, "categories": categories,
        "title": "Add Product",
    })


@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    games = Game.objects.all()
    sets = Set.objects.select_related("game").all()
    categories = Category.objects.filter(is_active=True).all()

    if request.method == "POST":
        product.name = request.POST.get("name", "").strip()
        product.description = request.POST.get("description", "")
        product.price = request.POST.get("price", "0")
        product.stock = request.POST.get("stock", "0")
        product.product_type = request.POST.get("product_type", "sealed")
        set_id = request.POST.get("set")
        product.set_id = set_id or None
        cat_id = request.POST.get("category")
        product.category_id = cat_id or None
        product.save()

        if product.product_type == "single_card":
            detail, _ = SingleCardDetail.objects.get_or_create(product=product)
            detail.rarity = request.POST.get("rarity", "")
            detail.language = request.POST.get("language", "")
            detail.condition = request.POST.get("condition", "")
            detail.save()

        for img in request.FILES.getlist("images"):
            ProductImage.objects.create(product=product, image=img)

        ActivityLog.objects.create(
            admin_user=request.user,
            action=f"Product updated: {product.name}",
            target_table="products",
            target_id=product.pk,
        )
        messages.success(request, f"Product '{product.name}' updated.")
        return redirect("admin_product_list")

    return render(request, "admin/product_form.html", {
        "product": product,
        "games": games, "sets": sets, "categories": categories,
        "title": "Edit Product",
    })


@admin_required
def admin_product_toggle(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.is_active = not p.is_active
    p.save()
    return redirect("admin_product_list")


# ---- Inventory ----


@admin_required
def admin_inventory(request):
    products = Product.objects.select_related("set", "game").all()
    low_stock = [p for p in products if 0 < p.stock < 5]
    out_of_stock = [p for p in products if p.stock == 0]
    return render(request, "admin/inventory.html", {
        "products": products,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
    })


@admin_required
def admin_inventory_update(request, pk):
    p = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        p.stock = int(request.POST.get("stock", 0))
        p.save()
        messages.success(request, f"{p.name} stock updated to {p.stock}.")
    return redirect("admin_inventory")
