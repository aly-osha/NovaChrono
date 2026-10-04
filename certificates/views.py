"""
certificates/views.py
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import AuthenticityCertificate
from products.models import Product
from analytics.models import ActivityLog
from .qr import attach_qr_urls, verification_url


def public_verify(request):
    """Public certificate verification page (FR-54..FR-58).

    Reachable three ways, all landing here:
      - manual code entry:  /certify/verify/?code=NC-1234
      - QR scan (FR-56):   the decoded QR URL IS this page with ?code=
      - printed label:     whatever absolute URL the QR encodes
    """
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

    context = {
        "code": code,
        "cert": cert,
        "found": found,
    }
    if cert:
        # FR-53: show the certificate's own QR so a buyer can re-verify or
        # save it. Computed, never stored.
        attach_qr_urls(request, [cert])
        context["qr_url"] = cert.qr_url
    return render(request, "certificates/verify.html", context)


def _is_admin(user):
    return user.is_authenticated and user.role in ("admin", "super_admin")


@login_required
@user_passes_test(_is_admin)
def admin_certificate_list(request):
    certs = list(AuthenticityCertificate.objects.select_related(
        "product", "issued_by",
    ).all())
    # FR-53: attach a computed QR URL per certificate for the admin to print / download.
    attach_qr_urls(request, certs)
    # Supply active products with prefetched certificates so admin can issue certificates
    products = Product.objects.filter(is_active=True).select_related(
        "set", "game"
    ).prefetch_related("certificates")
    return render(request, "certificates/admin_list.html", {
        "certs": certs,
        "products": products,
    })


@login_required
@user_passes_test(_is_admin)
def admin_certificate_create(request, pk):
    """Generate an authenticity certificate for a product."""
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
            status="valid",
            is_active=True,
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
@user_passes_test(_is_admin)
def admin_certificate_revoke(request, pk):
    """Revoke an active certificate."""
    cert = get_object_or_404(AuthenticityCertificate, pk=pk)
    cert.is_active = False
    cert.status = "revoked"
    cert.save()

    ActivityLog.objects.create(
        admin_user=request.user,
        action=f"Certificate revoked: {cert.verification_code}",
        target_table="authenticity_certificates",
        target_id=cert.pk,
    )

    messages.success(request, f"Certificate {cert.verification_code} revoked.")
    return redirect("admin_certificate_list")
