"""
notifications/views.py — the in-app notification centre (FR-25).

Lists the events monitoring raised (FR-22 price drop, FR-23 restock) and
lets the buyer mark them read. Notifications are per-user and read-scoped,
so there is no cross-buyer leakage.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification
from .monitoring import mark_all_read, unread_count


@login_required
def notification_list(request):
    """FR-25: in-app notification list for the signed-in buyer."""
    items = (
        Notification.objects
        .filter(buyer=request.user)
        .select_related("product")
    )
    unread = items.filter(is_read=False)
    read = items.filter(is_read=True)

    return render(request, "notifications/list.html", {
        "unread": unread,
        "read": read,
        "unread_count": unread_count(request.user),
    })


@require_POST
@login_required
def mark_read(request, pk):
    """Mark one notification read and return to the list."""
    n = get_object_or_404(Notification, pk=pk, buyer=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    return redirect("notification_list")


@require_POST
@login_required
def mark_all(request):
    """Clear the whole unread badge."""
    n = mark_all_read(request.user)
    if n:
        messages.success(request, f"{n} notification(s) marked as read.")
    return redirect("notification_list")
