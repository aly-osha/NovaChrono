import csv
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from accounts.decorators import staff_required, superadmin_required
from catalog.models import Product, ProductImage, Inventory, TCG, Category
from orders.models import Order, OrderItem, OrderStatusHistory, StoreSettings, Payment
from .models import ActivityLog
from .forms import ProductAdminForm, StaffCreateForm, StoreSettingsForm

User = get_user_model()


@staff_required
def overview_view(request):
    """
    Admin overview with KPI metrics, Chart.js datasets, and recent activities.
    """
    total_sales = Order.objects.filter(payment__status=Payment.Status.PAID).aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status__in=[Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PROCESSING]).count()
    total_products = Product.objects.count()
    total_buyers = User.objects.filter(role=User.Role.BUYER).count()
    low_stock_count = Inventory.objects.filter(stock_quantity__lte=F('low_stock_threshold')).count()

    recent_orders = Order.objects.select_related('user', 'payment').prefetch_related('items').order_by('-created_at')[:8]
    low_stock_items = Inventory.objects.filter(stock_quantity__lte=5).select_related('product', 'product__tcg')[:6]

    # Chart 1: Daily sales last 7 days
    today = timezone.now().date()
    days_labels = []
    sales_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days_labels.append(day.strftime('%b %d'))
        day_sales = Order.objects.filter(
            created_at__date=day,
            payment__status=Payment.Status.PAID
        ).aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        sales_data.append(float(day_sales))

    # Chart 2: Orders by Status
    status_counts = Order.objects.values('status').annotate(total=Count('id'))
    status_labels = [dict(Order.Status.choices).get(s['status'], s['status']) for s in status_counts]
    status_values = [s['total'] for s in status_counts]

    # Chart 3: Sales by TCG
    tcg_sales = OrderItem.objects.values('tcg_snapshot').annotate(total=Sum('subtotal')).order_by('-total')[:6]
    tcg_labels = [item['tcg_snapshot'] or 'Accessories' for item in tcg_sales]
    tcg_values = [float(item['total']) for item in tcg_sales]

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_products': total_products,
        'total_buyers': total_buyers,
        'low_stock_count': low_stock_count,
        'recent_orders': recent_orders,
        'low_stock_items': low_stock_items,
        # Chart JSON data
        'chart_days_labels': days_labels,
        'chart_sales_data': sales_data,
        'chart_status_labels': status_labels,
        'chart_status_values': status_values,
        'chart_tcg_labels': tcg_labels,
        'chart_tcg_values': tcg_values,
    }
    return render(request, 'dashboard/overview.html', context)


@staff_required
def products_list_view(request):
    products = Product.objects.select_related('tcg', 'category', 'inventory').prefetch_related('images').all()

    tcg_filter = request.GET.get('tcg')
    category_filter = request.GET.get('category')
    search_q = request.GET.get('q', '').strip()

    if tcg_filter:
        products = products.filter(tcg__slug=tcg_filter)
    if category_filter:
        products = products.filter(category__slug=category_filter)
    if search_q:
        products = products.filter(Q(name__icontains=search_q) | Q(sku__icontains=search_q))

    tcgs = TCG.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)

    return render(request, 'dashboard/products_list.html', {
        'products': products,
        'tcgs': tcgs,
        'categories': categories,
        'tcg_filter': tcg_filter,
        'category_filter': category_filter,
        'search_q': search_q,
    })


@staff_required
def product_add_view(request):
    if request.method == 'POST':
        form = ProductAdminForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()

            # Initialize Inventory
            stock_qty = form.cleaned_data.get('stock_quantity', 10)
            low_thresh = form.cleaned_data.get('low_stock_threshold', 5)
            Inventory.objects.create(
                product=product,
                stock_quantity=stock_qty,
                low_stock_threshold=low_thresh
            )

            # Images
            img1_file = form.cleaned_data.get('image_file_1')
            img1_url = form.cleaned_data.get('image_url_1')
            if img1_file or img1_url:
                ProductImage.objects.create(
                    product=product,
                    image=img1_file,
                    image_url=img1_url or '',
                    is_primary=True,
                    display_order=1
                )

            img2_file = form.cleaned_data.get('image_file_2')
            img2_url = form.cleaned_data.get('image_url_2')
            if img2_file or img2_url:
                ProductImage.objects.create(
                    product=product,
                    image=img2_file,
                    image_url=img2_url or '',
                    is_primary=False,
                    display_order=2
                )

            ActivityLog.log(request.user, f"Added Product: {product.name}", f"SKU: {product.sku}, Stock: {stock_qty}")
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect('dashboard:products_list')
    else:
        form = ProductAdminForm()

    return render(request, 'dashboard/product_form.html', {'form': form, 'title': 'Add New Product'})


@staff_required
def product_edit_view(request, product_id):
    product = get_object_or_404(Product.objects.select_related('inventory').prefetch_related('images'), id=product_id)

    if request.method == 'POST':
        form = ProductAdminForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()

            # Update or create inventory
            stock_qty = form.cleaned_data.get('stock_quantity', 10)
            low_thresh = form.cleaned_data.get('low_stock_threshold', 5)
            inv, _ = Inventory.objects.get_or_create(
                product=product,
                defaults={'stock_quantity': stock_qty, 'low_stock_threshold': low_thresh}
            )
            inv.stock_quantity = stock_qty
            inv.low_stock_threshold = low_thresh
            inv.save()

            # Primary Image
            img1_file = form.cleaned_data.get('image_file_1')
            img1_url = form.cleaned_data.get('image_url_1')
            pri = product.images.filter(is_primary=True).first()
            if img1_file or img1_url:
                if pri:
                    if img1_file:
                        pri.image = img1_file
                    if img1_url:
                        pri.image_url = img1_url
                    pri.save()
                else:
                    ProductImage.objects.create(
                        product=product,
                        image=img1_file,
                        image_url=img1_url or '',
                        is_primary=True,
                        display_order=1
                    )

            # Secondary Image
            img2_file = form.cleaned_data.get('image_file_2')
            img2_url = form.cleaned_data.get('image_url_2')
            sec = product.images.filter(is_primary=False).first()
            if img2_file or img2_url:
                if sec:
                    if img2_file:
                        sec.image = img2_file
                    if img2_url:
                        sec.image_url = img2_url
                    sec.save()
                else:
                    ProductImage.objects.create(
                        product=product,
                        image=img2_file,
                        image_url=img2_url or '',
                        is_primary=False,
                        display_order=2
                    )

            ActivityLog.log(request.user, f"Updated Product: {product.name}", f"SKU: {product.sku}")
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('dashboard:products_list')
    else:
        initial = {}
        if hasattr(product, 'inventory'):
            initial['stock_quantity'] = product.inventory.stock_quantity
            initial['low_stock_threshold'] = product.inventory.low_stock_threshold
        primary_img = product.images.filter(is_primary=True).first()
        if primary_img:
            initial['image_url_1'] = primary_img.image_url or (primary_img.image.url if primary_img.image else '')
        second_img = product.images.filter(is_primary=False).first()
        if second_img:
            initial['image_url_2'] = second_img.image_url or (second_img.image.url if second_img.image else '')

        form = ProductAdminForm(instance=product, initial=initial)

    primary_image_obj = product.images.filter(is_primary=True).first()
    secondary_image_obj = product.images.filter(is_primary=False).first()

    return render(request, 'dashboard/product_form.html', {
        'form': form,
        'product': product,
        'primary_image_obj': primary_image_obj,
        'secondary_image_obj': secondary_image_obj,
        'title': f'Edit {product.name}'
    })


@staff_required
@require_POST
def product_toggle_active_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    status_str = "Active" if product.is_active else "Inactive"
    ActivityLog.log(request.user, f"Toggled Product Status: {product.name} to {status_str}")
    messages.info(request, f"Product '{product.name}' is now {status_str}.")
    return redirect('dashboard:products_list')


@staff_required
def inventory_view(request):
    inventories = Inventory.objects.select_related('product', 'product__tcg').all().order_by('stock_quantity')

    status_filter = request.GET.get('status')
    if status_filter:
        inventories = inventories.filter(status=status_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        inventories = inventories.filter(Q(product__name__icontains=search_q) | Q(product__sku__icontains=search_q))

    return render(request, 'dashboard/inventory.html', {
        'inventories': inventories,
        'status_filter': status_filter,
        'search_q': search_q,
    })


@staff_required
@require_POST
def update_inventory_stock_view(request, inventory_id):
    inv = get_object_or_404(Inventory, id=inventory_id)
    new_qty = request.POST.get('stock_quantity')
    new_thresh = request.POST.get('low_stock_threshold')

    if new_qty is not None:
        try:
            inv.stock_quantity = max(0, int(new_qty))
        except ValueError:
            pass
    if new_thresh is not None:
        try:
            inv.low_stock_threshold = max(1, int(new_thresh))
        except ValueError:
            pass

    inv.save()
    ActivityLog.log(request.user, f"Updated Stock for {inv.product.name}", f"New Qty: {inv.stock_quantity}, Status: {inv.get_status_display()}")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'new_quantity': inv.stock_quantity,
            'status': inv.get_status_display(),
        })

    messages.success(request, f"Stock updated for {inv.product.name}.")
    return redirect('dashboard:inventory')


@staff_required
def orders_list_view(request):
    orders = Order.objects.select_related('user', 'payment', 'invoice').prefetch_related('items').all()

    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'ALL':
        orders = orders.filter(status=status_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders = orders.filter(
            Q(order_number__icontains=search_q) |
            Q(shipping_name__icontains=search_q) |
            Q(user__email__icontains=search_q) |
            Q(user__username__icontains=search_q)
        )

    return render(request, 'dashboard/orders_list.html', {
        'orders': orders,
        'status_filter': status_filter or 'ALL',
        'search_q': search_q,
        'order_statuses': Order.Status.choices,
    })


@staff_required
def order_detail_admin_view(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related('user', 'payment', 'invoice').prefetch_related('items', 'status_history'),
        order_number=order_number
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status':
            new_status = request.POST.get('new_status')
            note = request.POST.get('note', '').strip()
            carrier = request.POST.get('carrier', order.carrier).strip()
            tracking = request.POST.get('tracking_number', order.tracking_number).strip()

            if new_status in dict(Order.Status.choices) and new_status != order.status:
                prev = order.status
                order.status = new_status
                order.carrier = carrier
                order.tracking_number = tracking
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status=prev,
                    new_status=new_status,
                    changed_by=request.user,
                    note=note or f"Status changed to {order.get_status_display()} by {request.user.username}"
                )

                ActivityLog.log(
                    request.user,
                    f"Order #{order.order_number} Status Changed: {prev} -> {new_status}",
                    f"Tracking: {tracking}, Note: {note}"
                )
                messages.success(request, f"Order status updated to {order.get_status_display()}.")
                return redirect('dashboard:order_detail', order_number=order.order_number)

        elif action == 'save_notes':
            admin_notes = request.POST.get('admin_notes', '').strip()
            order.admin_notes = admin_notes
            order.save()
            messages.success(request, "Internal administrator notes saved.")
            return redirect('dashboard:order_detail', order_number=order.order_number)

    return render(request, 'dashboard/order_detail.html', {
        'order': order,
        'order_statuses': Order.Status.choices,
    })


@superadmin_required
def staff_list_view(request):
    staff_members = User.objects.filter(role__in=[User.Role.STAFF, User.Role.SUPERADMIN]).order_by('-created_at')
    return render(request, 'dashboard/staff_list.html', {'staff_members': staff_members})


@superadmin_required
def staff_create_view(request):
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.log(request.user, f"Created Staff Account: {user.username} ({user.get_role_display()})")
            messages.success(request, f"Staff account for {user.username} created.")
            return redirect('dashboard:staff_list')
    else:
        form = StaffCreateForm()

    return render(request, 'dashboard/staff_form.html', {'form': form})


@superadmin_required
@require_POST
def staff_toggle_suspend_view(request, user_id):
    staff_user = get_object_or_404(User, id=user_id)
    if staff_user == request.user:
        messages.error(request, "You cannot suspend your own Super Admin account.")
        return redirect('dashboard:staff_list')

    staff_user.is_suspended = not staff_user.is_suspended
    staff_user.save()
    action = "Suspended" if staff_user.is_suspended else "Reactivated"
    ActivityLog.log(request.user, f"{action} Staff Member: {staff_user.username}")
    messages.info(request, f"Staff member '{staff_user.username}' is now {action}.")
    return redirect('dashboard:staff_list')


@superadmin_required
@require_POST
def staff_delete_view(request, user_id):
    staff_user = get_object_or_404(User, id=user_id)
    if staff_user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('dashboard:staff_list')

    uname = staff_user.username
    staff_user.delete()
    ActivityLog.log(request.user, f"Deleted Staff Member: {uname}")
    messages.warning(request, f"Staff member '{uname}' removed.")
    return redirect('dashboard:staff_list')


@superadmin_required
def users_list_view(request):
    buyers = User.objects.filter(role=User.Role.BUYER).annotate(
        orders_count=Count('orders'),
        total_spent=Sum('orders__total_amount')
    ).order_by('-date_joined')

    search_q = request.GET.get('q', '').strip()
    if search_q:
        buyers = buyers.filter(Q(username__icontains=search_q) | Q(email__icontains=search_q))

    return render(request, 'dashboard/users_list.html', {'buyers': buyers, 'search_q': search_q})


@superadmin_required
@require_POST
def user_toggle_suspend_view(request, user_id):
    buyer = get_object_or_404(User, id=user_id, role=User.Role.BUYER)
    buyer.is_suspended = not buyer.is_suspended
    buyer.save()
    action = "Suspended" if buyer.is_suspended else "Reactivated"
    ActivityLog.log(request.user, f"{action} User: {buyer.username}")
    messages.info(request, f"User '{buyer.username}' has been {action.lower()}.")
    return redirect('dashboard:users_list')


@staff_required
def activity_logs_view(request):
    logs = ActivityLog.objects.select_related('user').all()[:150]
    return render(request, 'dashboard/activity_logs.html', {'logs': logs})


@superadmin_required
def store_settings_view(request):
    settings_obj = StoreSettings.get_settings()
    if request.method == 'POST':
        form = StoreSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            ActivityLog.log(request.user, "Updated Store Settings & Tax Configuration")
            messages.success(request, "Store settings and invoice preferences saved.")
            return redirect('dashboard:store_settings')
    else:
        form = StoreSettingsForm(instance=settings_obj)

    return render(request, 'dashboard/store_settings.html', {'form': form})


@staff_required
def export_csv_view(request, export_type):
    """
    Exports Orders, Products, Inventory, or Sales data to clean CSV format.
    """
    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

    if export_type == 'orders':
        response['Content-Disposition'] = f'attachment; filename="NovaChrono_Orders_{timestamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order Number', 'Date', 'Customer', 'Email', 'Status', 'Items Qty', 'Subtotal', 'Tax', 'Shipping', 'Total', 'Payment Status'])
        for o in Order.objects.select_related('user', 'payment').all():
            writer.writerow([
                o.order_number,
                o.created_at.strftime('%Y-%m-%d %H:%M'),
                o.shipping_name,
                o.user.email,
                o.get_status_display(),
                o.total_items,
                f"{o.subtotal:.2f}",
                f"{o.tax_amount:.2f}",
                f"{o.shipping_amount:.2f}",
                f"{o.total_amount:.2f}",
                o.payment.get_status_display() if hasattr(o, 'payment') else 'N/A'
            ])

    elif export_type == 'products':
        response['Content-Disposition'] = f'attachment; filename="NovaChrono_Products_{timestamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(['SKU', 'Name', 'TCG', 'Category', 'Condition', 'Price', 'Stock', 'Status', 'Active'])
        for p in Product.objects.select_related('tcg', 'category', 'inventory').all():
            writer.writerow([
                p.sku,
                p.name,
                p.tcg.name,
                p.category.name,
                p.get_condition_display(),
                f"{p.price:.2f}",
                p.current_stock,
                p.stock_status,
                'Yes' if p.is_active else 'No'
            ])

    elif export_type == 'inventory':
        response['Content-Disposition'] = f'attachment; filename="NovaChrono_Inventory_{timestamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(['SKU', 'Product Name', 'TCG', 'Stock Quantity', 'Low Stock Threshold', 'Status'])
        for inv in Inventory.objects.select_related('product', 'product__tcg').all():
            writer.writerow([
                inv.product.sku,
                inv.product.name,
                inv.product.tcg.name,
                inv.stock_quantity,
                inv.low_stock_threshold,
                inv.get_status_display()
            ])

    else:
        return redirect('dashboard:overview')

    ActivityLog.log(request.user, f"Exported CSV: {export_type.title()}")
    return response
