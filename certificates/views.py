"""
certificates/views.py
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import AuthenticityCertificate
from products.models import Product
from analytics.models import ActivityLog


def public_verify(request):
    """Public certificate verification page."""
    code = request.GET.get("code", "").strip().upper()
    cert = None
    found = False

    if code:
        try:
            cert = AuthenticityCertificate.objects.get(
                verification_code=code, is_active=True,
            )
            found = True
        except AuthenticityCertificate.DoesNotExist:
            found = False

    return render(request, "certificates/verify.html", {
        "code": code,
        "cert": cert,
        "found": found,
    })


@login_required
def admin_certificate_list(request):
    from django.contrib.auth.decorators import user_passes_test
    certs = AuthenticityCertificate.objects.select_related(
        "product", "issued_by",
    ).all()
    return render(request, "certificates/admin_list.html", {"certs": certs})


@login_required
def admin_certificate_create(request, pk):
    """Generate an authenticity certificate for a product."""
    from django.contrib.auth.decorators import user_passes_test

    product = get_object_or_404(Product, pk=pk, is_active=True)

    # check existing active cert
    existing = AuthenticityCertificate.objects.filter(
        product=product, is_active=True,
    ).first()

    if request.method == "POST":
        import secrets
        code = secrets.token_hex(6).upper()
        cert = AuthenticityCertificate.objects.create(
            product=product,
            verification_code=code,
            issued_by=request.user,
        )
        ActivityLog.objects.create(
            admin_user=request.user,
            action=f"Certificate issued: {code} for {product.name}",
            target_table="authenticity_certificates",
            target_id=cert.pk,
        )
        messages.success(request, f"Certificate {code} issued for {product.name}.")
        return redirect("admin_certificate_list")

    return render(request, "certificates/admin_create.html", {
        "product": product,
        "existing": existing,
    })


@login_required
def admin_certificate_revoke(request, pk):
    """Revoke an active certificate."""
    from django.contrib.auth.decorators import user_passes_test

    cert = get_object_or_404(AuthenticityCertificate, pk=pk)
    cert.is_active = False
    cert.save()

    ActivityLog.objects.create(
        admin_user=request.user,
        action=f"Certificate revoked: {cert.verification_code}",
        target_table="authenticity_certificates",
        target_id=cert.pk,
    )

    messages.success(request, f"Certificate {cert.verification_code} revoked.")
    return redirect("admin_certificate_list")
