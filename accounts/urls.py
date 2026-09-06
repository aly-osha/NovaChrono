from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('addresses/', views.addresses_view, name='addresses'),
    path('addresses/<int:address_id>/delete/', views.delete_address_view, name='delete_address'),
    path('addresses/<int:address_id>/default/', views.set_default_address_view, name='set_default_address'),
]
