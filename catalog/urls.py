from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('shop/', views.shop_view, name='shop'),
    path('shop/<slug:category_slug>/', views.shop_view, name='shop_category'),
    path('tcg/<slug:tcg_slug>/', views.shop_view, name='shop_tcg'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('search/', views.search_view, name='search'),
    path('api/quick-view/<int:product_id>/', views.quick_view_api, name='quick_view_api'),
    path('api/search-suggest/', views.search_suggest_api, name='search_suggest_api'),
]
