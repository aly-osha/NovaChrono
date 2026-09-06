from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def buyer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to continue.")
            return redirect(f"/accounts/login/?next={request.path}")
        if getattr(request.user, 'is_suspended', False):
            messages.error(request, "Your account has been suspended. Please contact support.")
            return redirect('accounts:logout')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Staff login required to access the admin portal.")
            return redirect(f"/accounts/login/?next={request.path}")
        if not (request.user.is_staff_member or request.user.is_staff):
            messages.error(request, "Access denied: Staff or Admin privileges required.")
            raise PermissionDenied("You do not have staff permissions to view this page.")
        if getattr(request.user, 'is_suspended', False):
            messages.error(request, "Account suspended.")
            return redirect('accounts:logout')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Super Admin credentials required.")
            return redirect(f"/accounts/login/?next={request.path}")
        if not (request.user.is_super_admin or request.user.is_superuser):
            messages.error(request, "Access restricted: Super Administrator permissions only.")
            raise PermissionDenied("Super Admin privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
