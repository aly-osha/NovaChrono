"""
novachrono/urls.py
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

import core.views as core
import accounts.views as accounts
import products.views as products
import cart.views as cart
import wishlists.views as wishlists
import notifications.views as notifs
import orders.views as orders
import reviews.views as reviews
import certificates.views as certs
import analytics.views as analytics
import products.admin_views as padmin

urlpatterns = [
    # ---- Core ----
    path("", core.home, name="home"),
    # NOTE: custom vault-admin routes are declared further below BEFORE
    # Django's built-in admin site — admin.site.urls greedily matches any
    # "admin/..." subpath and 404s internally, so it must come last.

    # ---- Auth ----
    path("register/", accounts.register, name="register"),
    path("login/", accounts.login_view, name="login"),
    path("logout/", accounts.logout_view, name="logout"),
    path("profile/", accounts.profile, name="profile"),
    path("addresses/", accounts.address_list, name="address_list"),
    path("addresses/add/", accounts.address_create, name="address_create"),
    path("addresses/<int:pk>/edit/", accounts.address_edit, name="address_edit"),
    path("addresses/<int:pk>/delete/", accounts.address_delete, name="address_delete"),

    # ---- Products ----
    path("shop/", products.catalogue, name="catalogue"),
    path("shop/<int:pk>/", products.product_detail, name="product_detail"),
    path("verify/", products.verify_certificate, name="verify_certificate"),
    path("api/sets/", products.api_sets, name="api_sets"),

    # ---- Cart ----
    path("cart/", cart.cart, name="cart"),
    path("cart/add/<int:pk>/", cart.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", cart.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", cart.cart_remove, name="cart_remove"),

    # ---- Wishlist (own app: wishlists + wishlist_items) ----
    path("wishlist/", wishlists.wishlist, name="wishlist"),
    path("wishlist/add/<int:pk>/", wishlists.add_to_wishlist, name="wishlist_add"),
    path("wishlist/remove/<int:pk>/", wishlists.remove_from_wishlist, name="wishlist_remove"),
    path("wishlist/to-cart/<int:pk>/", wishlists.wishlist_to_cart, name="wishlist_to_cart"),

    # ---- Notifications (FR-25 in-app; events from FR-22 / FR-23) ----
    path("notifications/", notifs.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", notifs.mark_read, name="notification_mark_read"),
    path("notifications/read-all/", notifs.mark_all, name="notification_mark_all"),
    path("admin/monitoring/run/", wishlists.check_monitoring_now, name="monitoring_run"),

    # ---- Checkout / Orders ----
    path("checkout/", orders.checkout, name="checkout"),
    path("orders/", orders.order_list, name="order_list"),
    path("orders/<int:pk>/", orders.order_detail, name="order_detail"),
    path("orders/<int:pk>/invoice/", orders.order_invoice_pdf, name="order_invoice_pdf"),

    # ---- Reviews ----
    path("reviews/add/<int:pk>/", reviews.add_review, name="add_review"),
    path("reviews/edit/<int:pk>/", reviews.edit_review, name="edit_review"),

    # ---- Certificates (public + admin) ----
    path("certify/verify/", certs.public_verify, name="certify_verify"),

    # ---- Admin area ----
    path("admin/products/", padmin.admin_product_list, name="admin_product_list"),
    path("admin/products/add/", padmin.admin_product_create, name="admin_product_create"),
    path("admin/products/<int:pk>/edit/", padmin.admin_product_edit, name="admin_product_edit"),
    path("admin/products/<int:pk>/toggle/", padmin.admin_product_toggle, name="admin_product_toggle"),
    path("admin/products/<int:pk>/delete/", padmin.admin_product_delete, name="admin_product_delete"),
    path("admin/games/", padmin.admin_game_list, name="admin_game_list"),
    path("admin/games/add/", padmin.admin_game_create, name="admin_game_create"),
    path("admin/games/<int:pk>/edit/", padmin.admin_game_edit, name="admin_game_edit"),
    path("admin/games/<int:pk>/delete/", padmin.admin_game_delete, name="admin_game_delete"),
    path("admin/sets/", padmin.admin_set_list, name="admin_set_list"),
    path("admin/sets/add/", padmin.admin_set_create, name="admin_set_create"),
    path("admin/sets/<int:pk>/edit/", padmin.admin_set_edit, name="admin_set_edit"),
    path("admin/sets/<int:pk>/delete/", padmin.admin_set_delete, name="admin_set_delete"),
    path("admin/categories/", padmin.admin_category_list, name="admin_category_list"),
    path("admin/categories/add/", padmin.admin_category_create, name="admin_category_create"),
    path("admin/categories/<int:pk>/edit/", padmin.admin_category_edit, name="admin_category_edit"),
    path("admin/categories/<int:pk>/toggle/", padmin.admin_category_toggle, name="admin_category_toggle"),
    path("admin/inventory/", padmin.admin_inventory, name="admin_inventory"),
    path("admin/inventory/<int:pk>/update/", padmin.admin_inventory_update, name="admin_inventory_update"),

    # orders admin
    path("admin/orders/", orders.admin_order_list, name="admin_order_list"),
    path("admin/orders/<int:pk>/", orders.admin_order_detail, name="admin_order_detail"),

    # reviews admin
    path("admin/reviews/", reviews.admin_review_list, name="admin_review_list"),
    path("admin/reviews/<int:pk>/", reviews.admin_review_detail, name="admin_review_detail"),

    # certificates admin
    path("admin/certificates/", certs.admin_certificate_list, name="admin_certificate_list"),
    path("admin/certificates/<int:pk>/create/", certs.admin_certificate_create, name="admin_certificate_create"),
    path("admin/certificates/<int:pk>/revoke/", certs.admin_certificate_revoke, name="admin_certificate_revoke"),

    # analytics
    path("admin/dashboard/", analytics.dashboard, name="admin_dashboard"),
    path("admin/activity/", analytics.activity_log, name="admin_activity_log"),
    path("admin/settings/", analytics.system_settings, name="system_settings"),

    # Django built-in admin site — MUST stay last (see note at top).
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
