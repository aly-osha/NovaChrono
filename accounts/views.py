from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import BuyerRegistrationForm, BuyerLoginForm, UserProfileForm, AddressForm
from .models import CustomUser, Address
from cart.models import Cart, CartItem
from wishlist.models import Wishlist


def register_view(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Initialize Wishlist for the buyer
            Wishlist.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f"Welcome to NovaChrono, {user.first_name or user.username}! Your collector account is active.")
            return redirect('catalog:home')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = BuyerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')

    redirect_to = request.GET.get('next', 'catalog:home')

    if request.method == 'POST':
        form = BuyerLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_suspended:
                messages.error(request, "Your account has been suspended. Please contact NovaChrono support.")
                return redirect('accounts:login')

            # Transfer guest cart if session exists
            session_key = request.session.session_key
            guest_cart = None
            if session_key:
                guest_cart = Cart.objects.filter(session_key=session_key).first()

            login(request, user)

            if guest_cart and guest_cart.items.exists():
                user_cart, _ = Cart.objects.get_or_create(user=user)
                for item in guest_cart.items.all():
                    existing_item = CartItem.objects.filter(cart=user_cart, product=item.product).first()
                    if existing_item:
                        existing_item.quantity += item.quantity
                        existing_item.save()
                    else:
                        item.cart = user_cart
                        item.save()
                guest_cart.delete()

            # Ensure buyer has a wishlist
            Wishlist.objects.get_or_create(user=user)

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            if user.is_staff_member and 'dashboard' in redirect_to:
                return redirect(redirect_to)
            elif user.is_staff_member and redirect_to == 'catalog:home':
                return redirect('dashboard:overview')
            return redirect(redirect_to)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = BuyerLoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': redirect_to})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out of NovaChrono.")
    return redirect('catalog:home')


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)

    recent_orders = user.orders.all()[:5]
    addresses = user.addresses.all()

    return render(request, 'accounts/profile.html', {
        'form': form,
        'recent_orders': recent_orders,
        'addresses': addresses,
        'orders_count': user.orders.count(),
        'wishlist_count': user.wishlist.item_count if hasattr(user, 'wishlist') else 0,
    })


@login_required
def addresses_view(request):
    user = request.user
    addresses = user.addresses.all()

    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user
            if not addresses.exists():
                address.is_default_shipping = True
                address.is_default_billing = True
            address.save()
            messages.success(request, "Address saved successfully.")
            return redirect('accounts:addresses')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = AddressForm()

    return render(request, 'accounts/addresses.html', {
        'addresses': addresses,
        'form': form,
    })


@login_required
def delete_address_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address removed.")
    return redirect('accounts:addresses')


@login_required
def set_default_address_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user).update(is_default_shipping=False)
    address.is_default_shipping = True
    address.save()
    messages.success(request, f"Default shipping address set to {address.full_name}.")
    return redirect('accounts:addresses')
