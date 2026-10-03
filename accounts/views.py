"""
accounts/views.py
"""
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
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
        user.role = "buyer"
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
def address_list(request):
    addresses = request.user.addresses.all()
    return render(request, "accounts/addresses.html", {"addresses": addresses})


@login_required
def address_create(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.buyer = request.user
            if addr.is_default:
                request.user.addresses.update(is_default=False)
            addr.save()
            messages.success(request, "Address saved.")
            return redirect("address_list")
    else:
        form = AddressForm()
    return render(request, "accounts/address_form.html", {"form": form, "title": "Add Address"})


@login_required
def address_edit(request, pk):
    addr = get_object_or_404(request.user.addresses, pk=pk)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=addr)
        if form.is_valid():
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
def address_delete(request, pk):
    addr = get_object_or_404(request.user.addresses, pk=pk)
    addr.delete()
    messages.success(request, "Address removed.")
    return redirect("address_list")
