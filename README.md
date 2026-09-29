# NovaChrono — Online TCG Buying Platform

Dark-luxury Django e-commerce store for trading card games, built from the
Software Requirement Specification + Stitch UI design system
(violet `#7928CA` / cyan `#00E5FF` / gold `#D4AF37` on obsidian `#121317`).

## Quick start

```bash
cd novachrono_build
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Open http://localhost:8000/

## Demo accounts

| Role   | Login email              | Password       |
|--------|--------------------------|----------------|
| Admin  | `admin@novachrono.com`   | `admin123`     |
| Buyer  | `collector@example.com`  | `collector123` |

> Usernames mirror emails (buyers sign up with email only) — always log in
> with the email address.

## What's implemented (per SRS)

- **Accounts (FR-1–8):** register/login/logout, unique-email validation,
  profile, delivery addresses, password hashing, RBAC (buyer/admin/super_admin).
- **Catalogue (FR-9–13):** games → sets → products; sealed / single-card /
  related types; single-card rarity/language/condition; product images.
- **Search & filter (FR-14–16):** keyword search + simultaneous filters
  (game, category, type, rarity, language, condition, price range, in-stock)
  + sorting.
- **Wishlist (FR-17–20):** save/remove/view/move-to-cart.
- **Cart & checkout (FR-25–33):** cart CRUD, subtotal, stock validation,
  shipping address, order summary, sandbox/mock payment, atomic order creation
  with stock decrement; failed payment creates nothing.
- **Orders (FR-34–37):** buyer history + detail with `Placed → Packed →
  Shipped → Delivered` timeline; admin order processing + status updates.
- **Reviews (FR-38–48):** purchase-verified 1–5★ reviews, edit own reviews,
  verified-purchase badges, average ratings, admin approve/hide/respond/remove.
- **Authenticity (FR-49–57):** admin-issued certificates with unique codes,
  public verification page (`/verify/` + `/certify/verify/`) showing the
  authenticity record or an invalid-code notice.
- **Price alerts (FR-21–22):** buyers set target-price watches from the
  product page modal (`PriceAlert` model); active alerts shown on the page.
- **Inventory (FR-62–67):** admin product/category/game/set CRUD, stock
  updates, low-stock (<5) and out-of-stock alerts.
- **Analytics (FR-68–69):** dashboard with daily/weekly/monthly sales, order
  counts, units sold, best sellers, inventory value, ratings, certificates.
- **Admin (FR-70–77):** user management via Django admin, categories, system
  settings, global activity log of admin actions.

## Important implementation notes

- Custom vault-admin URLs (`admin/dashboard/`, `admin/products/`, …) are
  declared **before** `admin.site.urls` in `novachrono/urls.py` — Django's
  admin site greedily swallows unknown `admin/...` subpaths, so it must come
  last. Do not reorder.
- `Product.avg_rating` is a model property; never `.annotate(avg_rating=…)`
  on Product querysets (use `annotated_rating`). Same rule for any property
  name: `active_product_count`, `active_certificate`, `line_total`.
- No queryset calls, no `|mulitem`-style custom filters, no `?:` ternaries in
  templates — Django templates support none of these. Compute in views/models.
- SQLite is configured for dev; point `DATABASES` at PostgreSQL for production
  and set a real `SECRET_KEY` / `DEBUG=False`.
