"""
certificates/qr.py — QR encode + decode for FR-53 / FR-56.

Deliberately does NOT change the database schema.

The QR code contains nothing but a URL that already exists:

    https://<host>/certify/verify/?code=<verification_code>

That is the same page `public_verify` already serves (it reads `?code=`),
so a scan needs no new route, no new table and no stored image. The URL is
COMPUTED from the certificate at display time rather than persisted, which
means it is always correct: change the host, and old certificates still
resolve correctly instead of pointing at a stale domain.

`qr_code_url` on the model is left exactly as it is. If it has been filled
in by an admin, that stored value wins (so a deliberately customised QR
still works); otherwise the computed URL is used.

Rendering is client-side via a CDN library (qrcodejs). That keeps Pillow,
reportlab and any binary QR dependency out of requirements.txt — which
matters here because the project's manifest was deliberately trimmed to
Django alone.
"""

from django.urls import reverse


def verification_url(request, cert):
    """The absolute URL a QR code for this certificate should encode.

    Returns the admin-supplied `qr_code_url` when present, otherwise the
    canonical verify URL built from the current request.
    """
    stored = (getattr(cert, "qr_code_url", "") or "").strip()
    if stored:
        return stored

    path = reverse("certify_verify")
    code = cert.verification_code
    return request.build_absolute_uri(f"{path}?code={code}")


def attach_qr_urls(request, certs):
    """Return `certs` annotated with a `.qr_url` attribute for the template.

    Kept out of the template so the URL-building logic is testable in Python
    rather than being smeared across markup.
    """
    for cert in certs:
        cert.qr_url = verification_url(request, cert)
    return certs