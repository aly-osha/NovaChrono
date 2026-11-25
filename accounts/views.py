"""
accounts/views.py
"""
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods, require_POST
from django import forms
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import User, Address


def _safe_next_url(next_url, request):
    """Validate a ?next= redirect target before sending a user there.

    Without this check, /login/?next=https://evil.example could bounce a
    freshly-authenticated user off-site (open redirect). Only relative
    paths and absolute URLs on this host are allowed; anything else falls
    back to the home page.
    """
    if not next_url:
        return reverse("home")
    allowed = {request.get_host()}
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts=allowed,
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("home")


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(
        widget=forms.PasswordInput, label="Confirm password"
    )
    class Meta:
        model = User
        fields = ["name", "email", "password1", "password2", "phone"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        # AbstractUser requires a unique username but buyers sign up with
        # email only — mirror the (unique, validated) email into username.
        user.username = user.email
        user.set_password(self.cleaned_data["password1"])
        user.is_superuser = False
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "phone"]

    def clean_email(self):
        """FR-3: reject an email already used by a different account.

        The DB now enforces UNIQUE, but SQLite compares text case-sensitively,
        so 'A@b.com' and 'a@b.com' would both pass at the storage layer.
        Registration already lowercases; do the same here so the two entry
        points agree.
        """
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["line1", "line2", "city", "state", "postal_code", "country", "is_default"]


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    # Where to go after a successful sign-in. When @login_required bounced
    # the user here it appended ?next=<the page they wanted>, so honour it
    # instead of always dropping them on the home page.
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            # Resolve the account by email, then authenticate against its
            # actual username (usernames mirror emails for buyer accounts,
            # but legacy/seed accounts may differ).
            try:
                account = User.objects.get(email__iexact=email)
                username = account.username
            except User.DoesNotExist:
                username = email
            user = authenticate(
                request,
                username=username,
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.get_full_name() or user.email}.")
                return redirect(_safe_next_url(next_url, request))
            messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {
        "form": form,
        "next": next_url,
    })


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            # Keep username mirrored to email (see RegisterForm.save).
            user.username = user.email
            user.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect("profile")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, "accounts/password_change.html", {"form": form})


@login_required
def address_list(request):
    addresses = request.user.addresses.order_by("-is_default", "-updated_at")
    return render(request, "accounts/addresses.html", {"addresses": addresses})


@login_required
def address_create(request):
    raw_next = request.GET.get("next") or request.POST.get("next") or ""
    next_url = _safe_next_url(raw_next, request) if raw_next else ""
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                addr = form.save(commit=False)
                addr.buyer = request.user
                if addr.is_default:
                    request.user.addresses.update(is_default=False)
                addr.save()
            messages.success(request, "Address saved.")
            return redirect(next_url or "address_list")
    else:
        form = AddressForm()
    return render(
        request,
        "accounts/address_form.html",
        {"form": form, "title": "Add Address", "next": next_url},
    )


@login_required
def address_edit(request, pk):
    addr = get_object_or_404(request.user.addresses, pk=pk)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=addr)
        if form.is_valid():
            with transaction.atomic():
                addr = form.save(commit=False)
                if addr.is_default:
                    request.user.addresses.exclude(pk=pk).update(is_default=False)
                addr.save()
            messages.success(request, "Address updated.")
            return redirect("address_list")
    else:
        form = AddressForm(instance=addr)
    return render(request, "accounts/address_form.html", {"form": form, "title": "Edit Address"})


@login_required
@require_POST
def address_delete(request, pk):
    from orders.models import Order

    addr = get_object_or_404(request.user.addresses, pk=pk)
    was_default = addr.is_default
    with transaction.atomic():
        # Preserve snapshot on any legacy orders before SET_NULL clears the FK.
        Order.objects.filter(
            shipping_address=addr, shipping_address_line1="",
        ).update(**addr.as_dict)
        addr.delete()
        if was_default:
            replacement = request.user.addresses.order_by("-updated_at", "-id").first()
            if replacement:
                replacement.is_default = True
                replacement.save(update_fields=["is_default", "updated_at"])
    messages.success(request, "Address removed.")
    return redirect("address_list")


# ---- Admin user management views ----

def _is_admin(user):
    return user.is_authenticated and user.is_superuser


class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "phone", "status", "is_superuser"]


@login_required
@user_passes_test(_is_admin)
def admin_user_list(request):
    q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()

    users_qs = User.objects.annotate(
        order_count=Count("orders", distinct=True),
        address_count=Count("addresses", distinct=True),
    ).order_by("-date_joined")

    if q:
        users_qs = users_qs.filter(
            Q(email__icontains=q) | Q(name__icontains=q) | Q(phone__icontains=q)
        )
    if role_filter == "admin":
        users_qs = users_qs.filter(is_superuser=True)
    elif role_filter == "buyer":
        users_qs = users_qs.filter(is_superuser=False)
    if status_filter in {"active", "inactive", "suspended"}:
        users_qs = users_qs.filter(status=status_filter)

    stats = {
        "total": User.objects.count(),
        "active": User.objects.filter(status="active").count(),
        "suspended": User.objects.filter(status="suspended").count(),
        "admins": User.objects.filter(is_superuser=True).count(),
    }

    return render(request, "admin/user_list.html", {
        "users": users_qs,
        "stats": stats,
        "q": q,
        "role_filter": role_filter,
        "status_filter": status_filter,
    })


@login_required
@user_passes_test(_is_admin)
def admin_user_detail(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            updated = form.save(commit=False)
            if target_user.pk == request.user.pk:
                if updated.status != "active":
                    messages.error(request, "You cannot suspend or deactivate your own admin account.")
                    return redirect("admin_user_detail", pk=pk)
                if not updated.is_superuser:
                    messages.error(request, "You cannot remove your own admin privileges.")
                    return redirect("admin_user_detail", pk=pk)
            updated.save()
            messages.success(request, f"Updated user {target_user.email}.")
            return redirect("admin_user_detail", pk=pk)
    else:
        form = AdminUserEditForm(instance=target_user)

    addresses = target_user.addresses.order_by("-is_default", "-updated_at")
    orders = target_user.orders.order_by("-created_at")[:10]
    return render(request, "admin/user_detail.html", {
        "target_user": target_user,
        "form": form,
        "addresses": addresses,
        "orders": orders,
    })


@login_required
@user_passes_test(_is_admin)
@require_POST
def admin_user_toggle_status(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user.pk == request.user.pk:
        messages.error(request, "You cannot suspend your own admin account.")
        return redirect("admin_user_list")

    target_user.status = "suspended" if target_user.status == "active" else "active"
    target_user.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{target_user.email} is now {target_user.get_status_display()}.")
    next_url = _safe_next_url(request.POST.get("next", ""), request) if request.POST.get("next") else ""
    return redirect(next_url or "admin_user_list")


@login_required
@user_passes_test(_is_admin)
@require_POST
def admin_user_toggle_role(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user.pk == request.user.pk:
        messages.error(request, "You cannot remove your own admin privileges.")
        return redirect("admin_user_list")

    target_user.is_superuser = not target_user.is_superuser
    target_user.save()
    role_label = "Admin" if target_user.is_superuser else "Customer"
    messages.success(request, f"{target_user.email} role set to {role_label}.")
    next_url = _safe_next_url(request.POST.get("next", ""), request) if request.POST.get("next") else ""
    return redirect(next_url or "admin_user_list")
