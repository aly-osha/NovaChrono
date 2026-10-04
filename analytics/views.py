"""
analytics/views.py
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta

from products.models import Product
from orders.models import Order, OrderItem
from reviews.models import Review
from certificates.models import AuthenticityCertificate
from analytics.models import ActivityLog, SystemSetting


def _is_admin(user):
    return user.is_authenticated and user.role in ("admin", "super_admin")


def admin_required(view_func):
    return user_passes_test(_is_admin)(view_func)


@admin_required
def dashboard(request):
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # sales
    daily_sales = Order.objects.filter(
        created_at__date=today,
        status__in=("placed", "packed", "shipped", "delivered"),
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    weekly_orders = Order.objects.filter(
        created_at__gte=week_ago,
    ).count()

    monthly_revenue = Order.objects.filter(
        created_at__gte=month_ago,
        status__in=("placed", "packed", "shipped", "delivered"),
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    # products sold this week
    products_sold = OrderItem.objects.filter(
        order__created_at__gte=week_ago,
    ).aggregate(count=Sum("quantity"))["count"] or 0

    # best-selling products (last 30 days)
    best_sellers = OrderItem.objects.filter(
        order__created_at__gte=month_ago,
    ).values("product__name", "product__pk").annotate(
        total_sold=Sum("quantity"),
    ).order_by("-total_sold")[:5]

    # low stock
    low_stock = Product.objects.filter(
        stock__gt=0, stock__lt=5, is_active=True,
    ).select_related("set", "game")[:10]

    # out of stock
    out_of_stock = Product.objects.filter(
        stock=0, is_active=True,
    ).select_related("set", "game")[:10]

    # inventory value
    inventory_value = Product.objects.filter(is_active=True).aggregate(
        value=Sum(F("price") * F("stock")),
    )["value"] or 0

    # pending orders
    pending_orders = Order.objects.filter(status="placed").count()

    # recent activity
    recent_activity = ActivityLog.objects.select_related("admin_user")[:20]

    # review stats
    total_reviews = Review.objects.filter(is_approved=True).count()
    avg_product_rating = Product.objects.annotate(
        r=Avg("reviews__rating"),
    ).aggregate(avg=Avg("r"))["avg"] or 0

    # certificate stats
    total_certs = AuthenticityCertificate.objects.filter(is_active=True).count()

    return render(request, "analytics/dashboard.html", {
        "daily_sales": daily_sales,
        "weekly_orders": weekly_orders,
        "monthly_revenue": monthly_revenue,
        "products_sold": products_sold,
        "best_sellers": best_sellers,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "inventory_value": inventory_value,
        "pending_orders": pending_orders,
        "recent_activity": recent_activity,
        "total_reviews": total_reviews,
        "avg_product_rating": round(avg_product_rating, 1),
        "total_certs": total_certs,
    })


@admin_required
def activity_log(request):
    logs = ActivityLog.objects.select_related("admin_user").all()
    return render(request, "analytics/activity_log.html", {"logs": logs})


@admin_required
def system_settings(request):
    if request.method == "POST":
        key = request.POST.get("setting_key", "").strip()
        value = request.POST.get("setting_value", "").strip()
        if key:
            obj, _ = SystemSetting.objects.update_or_create(
                setting_key=key,
                defaults={"setting_value": value, "updated_by": request.user},
            )
            messages.success(request, f"Setting '{key}' saved.")
            return redirect("system_settings")

    settings = SystemSetting.objects.all()
    return render(request, "analytics/settings.html", {"settings": settings})
