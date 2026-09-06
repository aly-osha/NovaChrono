from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview_view, name='overview'),
    # Products
    path('products/', views.products_list_view, name='products_list'),
    path('products/add/', views.product_add_view, name='product_add'),
    path('products/<int:product_id>/edit/', views.product_edit_view, name='product_edit'),
    path('products/<int:product_id>/toggle/', views.product_toggle_active_view, name='product_toggle_active'),
    # Inventory
    path('inventory/', views.inventory_view, name='inventory'),
    path('inventory/<int:inventory_id>/update/', views.update_inventory_stock_view, name='update_inventory_stock'),
    # Orders
    path('orders/', views.orders_list_view, name='orders_list'),
    path('orders/<str:order_number>/', views.order_detail_admin_view, name='order_detail'),
    # Staff (Super Admin)
    path('staff/', views.staff_list_view, name='staff_list'),
    path('staff/create/', views.staff_create_view, name='staff_create'),
    path('staff/<int:user_id>/suspend/', views.staff_toggle_suspend_view, name='staff_toggle_suspend'),
    path('staff/<int:user_id>/delete/', views.staff_delete_view, name='staff_delete'),
    # Users
    path('users/', views.users_list_view, name='users_list'),
    path('users/<int:user_id>/suspend/', views.user_toggle_suspend_view, name='user_toggle_suspend'),
    # System
    path('activity/', views.activity_logs_view, name='activity_logs'),
    path('settings/', views.store_settings_view, name='store_settings'),
    path('export/<str:export_type>/', views.export_csv_view, name='export_csv'),
]
