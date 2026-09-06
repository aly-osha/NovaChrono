from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('confirmation/<str:order_number>/', views.order_confirmation_view, name='confirmation'),
    path('history/', views.order_history_view, name='history'),
    path('<str:order_number>/', views.order_detail_view, name='detail'),
    path('<str:order_number>/cancel/', views.cancel_order_view, name='cancel'),
    # Documents
    path('<str:order_number>/invoice/', views.invoice_detail_view, name='invoice_detail'),
    path('<str:order_number>/invoice/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('<str:order_number>/packing-slip/', views.packing_slip_view, name='packing_slip'),
    path('<str:order_number>/shipping-label/', views.shipping_label_view, name='shipping_label'),
]
