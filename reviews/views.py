"""
reviews/views.py
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Avg

from .models import Review
from products.models import Product
from orders.models import OrderItem


@login_required
def add_review(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)

    # verify purchase
    has_purchased = OrderItem.objects.filter(
        order__buyer=request.user,
        product=product,
    ).exists()

    if not has_purchased:
        messages.error(request, "You must purchase this product before reviewing it.")
        return redirect("product_detail", pk=pk)

    # check for existing review
    existing = Review.objects.filter(
        buyer=request.user, product=product,
    ).first()

    if request.method == "POST":
        rating = int(request.POST.get("rating", 0))
        comment = request.POST.get("comment", "").strip()

        if rating < 1 or rating > 5:
            messages.error(request, "Rating must be between 1 and 5 stars.")
            return redirect("product_detail", pk=pk)

        if existing:
            existing.rating = rating
            existing.comment = comment
            existing.save()
            messages.success(request, "Review updated.")
        else:
            Review.objects.create(
                buyer=request.user,
                product=product,
                rating=rating,
                comment=comment,
                is_verified_purchase=True,
                is_approved=True,
            )
            messages.success(request, "Review submitted. Thank you!")

        return redirect("product_detail", pk=pk)

    return render(request, "reviews/add_review.html", {
        "product": product,
        "existing": existing,
        "has_purchased": has_purchased,
    })


@login_required
def edit_review(request, pk):
    review = get_object_or_404(
        Review.objects.select_related("product"),
        pk=pk, buyer=request.user,
    )

    if request.method == "POST":
        rating = int(request.POST.get("rating", 0))
        comment = request.POST.get("comment", "").strip()

        if rating < 1 or rating > 5:
            messages.error(request, "Rating must be between 1 and 5 stars.")
            return redirect("edit_review", pk=pk)

        review.rating = rating
        review.comment = comment
        review.save()
        messages.success(request, "Review updated.")
        return redirect("product_detail", pk=review.product.pk)

    return render(request, "reviews/edit_review.html", {"review": review})


# ---- Admin review moderation ----

def _is_admin(user):
    return user.is_authenticated and user.role in ("admin", "super_admin")


@login_required
@user_passes_test(_is_admin)
def admin_review_list(request):
    reviews = Review.objects.select_related("buyer", "product").all()
    return render(request, "reviews/admin_list.html", {"reviews": reviews})


@login_required
@user_passes_test(_is_admin)
def admin_review_detail(request, pk):
    from analytics.models import ActivityLog

    review = get_object_or_404(
        Review.objects.select_related("buyer", "product"),
        pk=pk,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "approve":
            review.is_approved = True
            review.status = "approved"
            review.save()
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Review #{review.pk} approved",
                target_table="reviews",
                target_id=review.pk,
            )
            messages.success(request, "Review approved.")
        elif action == "hide":
            review.is_approved = False
            review.status = "pending"
            review.save()
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Review #{review.pk} hidden",
                target_table="reviews",
                target_id=review.pk,
            )
            messages.success(request, "Review hidden.")
        elif action == "response":
            review.admin_response = request.POST.get("admin_response", "")
            review.save()
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Response added to Review #{review.pk}",
                target_table="reviews",
                target_id=review.pk,
            )
            messages.success(request, "Admin response added.")
        elif action == "remove":
            pk_val = review.pk
            review.delete()
            ActivityLog.objects.create(
                admin_user=request.user,
                action=f"Review #{pk_val} removed",
                target_table="reviews",
                target_id=pk_val,
            )
            messages.success(request, "Review permanently removed.")
            return redirect("admin_review_list")

        return redirect("admin_review_detail", pk=pk)

    return render(request, "reviews/admin_detail.html", {"review": review})
