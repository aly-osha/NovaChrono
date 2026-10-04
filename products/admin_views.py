from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.utils import timezone

from .models import Product, Game, Set, Category, SingleCardDetail, ProductImage, SealedPack
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
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.POST.get("is_ajax") == "1"
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        if not name:
            if is_ajax:
                return JsonResponse({"status": "error", "message": "Game name is required."}, status=400)
            messages.error(request, "Game name is required.")
        elif Game.objects.filter(name__iexact=name).exists():
            if is_ajax:
                return JsonResponse({"status": "error", "message": "A game with this name already exists."}, status=400)
            messages.error(request, "A game with this name already exists.")
        else:
            game = Game.objects.create(name=name, description=description, is_active=True)
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Game created: {name}",
                target_table="games",
                target_id=game.pk,
            )
            messages.success(request, f"Game '{name}' created successfully.")
            if is_ajax:
                return JsonResponse({"status": "success", "id": game.pk, "name": game.name})
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("admin_game_list")
    return render(request, "admin/game_form.html", {"title": "Add Game", "next": request.GET.get("next", "")})


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
    """Delete a game (FR-73).

    Two problems this fixes:
      1. It deleted on a plain GET, so a prefetch/hover could destroy data.
         Writes now require POST.
      2. Products reference a game with on_delete=PROTECT (schema integrity),
         so deleting a game in use raised ProtectedError -> HTTP 500. That is
         now a friendly message instead of a crash.
    """
    game = get_object_or_404(Game, pk=pk)

    if request.method != "POST":
        # Confirm page for a destructive action.
        in_use = Product.objects.filter(game=game).count()
        return render(request, "admin/delete_confirm.html", {
            "title": "Delete Game",
            "object_label": game.name,
            "cancel_url": "admin_game_list",
            "in_use_count": in_use,
            "blocked_message": (
                f"'{game.name}' is used by {in_use} product(s) and cannot be "
                f"deleted. Deactivate those products first, or rename this "
                f"game instead."
            ) if in_use else "",
        })

    in_use = Product.objects.filter(game=game).count()
    if in_use:
        messages.error(
            request,
            f"'{game.name}' is used by {in_use} product(s) and cannot be deleted.",
        )
        return redirect("admin_game_list")

    name = game.name
    game.delete()
    messages.success(request, f"Game '{name}' deleted.")
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
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.POST.get("is_ajax") == "1"
    if request.method == "POST":
        game_id = request.POST.get("game")
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        if not game_id or not name:
            err = "Please select a game and provide a set name."
            if is_ajax:
                return JsonResponse({"status": "error", "message": err}, status=400)
            messages.error(request, err)
        elif Set.objects.filter(game_id=game_id, name__iexact=name).exists():
            err = f"A set with name '{name}' already exists for this game."
            if is_ajax:
                return JsonResponse({"status": "error", "message": err}, status=400)
            messages.error(request, err)
        else:
            s = Set.objects.create(game_id=game_id, name=name, code=code, is_active=True)
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Set created: {name} ({s.game.name})",
                target_table="sets",
                target_id=s.pk,
            )
            messages.success(request, f"Set '{name}' created successfully.")
            if is_ajax:
                return JsonResponse({
                    "status": "success",
                    "id": s.pk,
                    "name": s.name,
                    "game_id": s.game_id,
                    "game_name": s.game.name,
                    "display_name": f"{s.game.name} — {s.name}"
                })
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("admin_set_list")
    return render(request, "admin/set_form.html", {"games": games, "title": "Add Set", "next": request.GET.get("next", "")})


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
    qs = Product.objects.select_related("set", "game", "category", "set__game").prefetch_related("images").all()
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

        if not game_id:
            messages.error(request, "Game is required.")
            return render(request, "admin/product_form.html", {
                "games": games, "sets": sets, "categories": categories,
                "title": "Add Product",
            })

        if not category_id:
            messages.error(request, "Category is required.")
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
                game_id=game_id,
                set_id=set_id or None,
                category_id=category_id,
            )

            if product_type == "sealed":
                SealedPack.objects.create(product=product)
            elif product_type == "single_card":
                SingleCardDetail.objects.create(
                    product=product,
                    rarity=request.POST.get("rarity", ""),
                    language=request.POST.get("language", ""),
                    condition=request.POST.get("condition", "near_mint"),
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
        game_id = request.POST.get("game")
        if game_id:
            product.game_id = game_id
        set_id = request.POST.get("set")
        product.set_id = set_id or None
        cat_id = request.POST.get("category")
        if cat_id:
            product.category_id = cat_id
        product.save()

        if product.product_type == "sealed":
            SealedPack.objects.get_or_create(product=product)
            SingleCardDetail.objects.filter(product=product).delete()
        elif product.product_type == "single_card":
            SealedPack.objects.filter(product=product).delete()
            detail, _ = SingleCardDetail.objects.get_or_create(product=product)
            detail.rarity = request.POST.get("rarity", "")
            detail.language = request.POST.get("language", "")
            detail.condition = request.POST.get("condition", "near_mint")
            detail.save()
        else:
            SealedPack.objects.filter(product=product).delete()
            SingleCardDetail.objects.filter(product=product).delete()

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
    """Activate / deactivate a product (FR-63).

    Requires POST. This used to flip the flag on a plain GET, which meant a
    link prefetch, a browser resend, or a stray crawler could silently
    deactivate a product in the live catalogue.
    """
    if request.method != "POST":
        # Preserve the old click-to-toggle affordance without the GET hazard:
        # bounce to a tiny form that POSTs back to this URL.
        p = get_object_or_404(Product, pk=pk)
        return render(request, "admin/toggle_confirm.html", {
            "product": p,
            "will_activate": not p.is_active,
        })

    p = get_object_or_404(Product, pk=pk)
    p.is_active = not p.is_active
    p.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"{p.name} {'activated' if p.is_active else 'deactivated'}.",
    )
    return redirect("admin_product_list")


@admin_required
def admin_product_delete(request, pk):
    """Delete a product.

    - POST removes the product and associated assets.
    - If the product is part of existing orders (on_delete=PROTECT on OrderItem),
      deletion is blocked to preserve historical orders/receipts; admin is advised to deactivate it.
    - On GET, displays a confirmation page (using admin/delete_confirm.html) with warnings.
    - Records an ActivityLog entry when deleted.
    """
    product = get_object_or_404(Product, pk=pk)
    orders_count = product.order_items.count()

    if request.method != "POST":
        return render(request, "admin/delete_confirm.html", {
            "title": "Delete Product",
            "object_label": product.name,
            "cancel_url": "admin_product_list",
            "in_use_count": orders_count,
            "blocked_message": (
                f"'{product.name}' has been purchased in {orders_count} customer order(s) "
                f"and cannot be deleted to preserve order records. "
                f"You can deactivate it instead to remove it from the store."
            ) if orders_count else "",
            "warning_message": (
                "This cannot be undone. All product images, listings, and details "
                "for this item will be permanently removed."
            ),
        })

    if orders_count:
        messages.error(
            request,
            f"'{product.name}' has been purchased in {orders_count} customer order(s) and cannot be deleted. Deactivate it instead.",
        )
        return redirect("admin_product_list")

    name = product.name
    product_pk = product.pk
    try:
        product.delete()
        ActivityLog.objects.create(
            admin_user=request.user,
            action=f"Product deleted: {name}",
            target_table="products",
            target_id=product_pk,
        )
        messages.success(request, f"Product '{name}' was successfully deleted.")
    except Exception as e:
        messages.error(request, f"Could not delete product: {e}")

    return redirect("admin_product_list")


# ---- Inventory ----


@admin_required
def admin_inventory(request):
    products = Product.objects.select_related("set", "game", "set__game").prefetch_related("images").all()
    low_stock = [p for p in products if 0 < p.stock < 5]
    out_of_stock = [p for p in products if p.stock == 0]
    return render(request, "admin/inventory.html", {
        "products": products,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
    })


@admin_required
def admin_inventory_update(request, pk):
    """Edit one product's stock count (FR-64).

    The inventory table's "Update Stock" control links here with a GET, so
    GET renders the edit form and POST saves it. Previously this view only
    read request.POST, so following that link did nothing at all: the
    quantity typed in the URL was ignored and the page just redirected back.
    """
    p = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        raw = request.POST.get("stock", "").strip()
        try:
            new_stock = int(raw)
            if new_stock < 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Enter a whole number of items (0 or more).")
            return redirect("admin_inventory")
        old_stock = p.stock
        p.stock = new_stock
        p.save(update_fields=["stock", "updated_at"])

        if new_stock == 0:
            from wishlists.models import WishlistItem
            WishlistItem.objects.filter(product=p).update(was_out_of_stock=True)
        elif old_stock == 0 and new_stock > 0:
            from notifications.monitoring import run_monitoring
            run_monitoring()

        ActivityLog.objects.create(
            admin_user=request.user,
            action=f"Stock updated for {p.name}: {old_stock} → {new_stock}",
            target_table="products",
            target_id=p.pk,
        )
        messages.success(request, f"{p.name} stock updated to {p.stock}.")
        return redirect("admin_inventory")

    return render(request, "admin/inventory_edit.html", {
        "product": p,
        "current_stock": p.stock,
    })
