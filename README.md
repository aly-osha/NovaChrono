# NOVACHRONO
> *"Collect. Discover. Trade."*

NovaChrono is a full-stack trading-card e-commerce platform and vault archive specializing in Pokémon, One Piece, Yu-Gi-Oh!, Magic: The Gathering, Dragon Ball Super, Gundam, and collector accessories.

NovaChrono is designed as a **centrally managed store** rather than a peer-to-peer marketplace. All inventory, authentications, packaging, and fulfillment operations are supervised by certified store specialists.

---

## Key Highlights & Architectural Features

1. **Role-Based Access Control (RBAC)**:
   - **Guest**: Browse products, universes, categories, search, live autocomplete.
   - **Buyer**: Add to cart, maintain personal wishlist, checkout with mock payment, track order timeline, download PDF invoices.
   - **Staff / Admin**: Operations portal, product CRUD, inventory threshold adjustments, order status progression, packing slips, shipping labels.
   - **Super Admin**: Full platform control, staff account creation/suspension, user management, store and tax configuration, CSV exports.

2. **Editorial UI / UX (Fable & Luxury Magazine Inspired)**:
   - Warm ivory aesthetic (`#F7F4EE`), charcoal typography (`#111111`), and electric cosmic violet accents (`#6342FF`).
   - Space Grotesk editorial headings paired with Inter body typography.
   - Rounded cards (`border-radius: 24px`), starburst stickers, floating hero compositions, micro-animations.
   - Live debounced search modal (`/api/search-suggest/`) and Quick View product previews (`/api/quick-view/<id>/`).

3. **Order Lifecycle & Complete Document Management**:
   - **Atomic Order Processing**: Enforced database transactions (`transaction.atomic`) guarantee stock reduction and payment record creation before invoice issuance.
   - **Order Timeline**: Visual progression through `Placed` → `Confirmed` → `Processing` → `Packed` → `Shipped` → `Delivered`.
   - **Printable Invoices (`@media print`)**: Clean, border-stamped A4 invoice layout that automatically removes headers, navbars, and buttons during printing.
   - **PDF Invoice Generation**: Instant downloadable A4 binary PDFs generated using **ReportLab** (`NovaChrono_Invoice_NC-2026-XXXXXX.pdf`).
   - **Warehouse Packing Slips**: Item checklists (`[ ] Verified`), SKU mappings, and inspection sign-offs with sensitive payment details omitted.
   - **Carrier Shipping Labels**: 4x6 label layout with simulated barcodes and tracking IDs.

4. **Custom Operations Portal (Admin Dashboard)**:
   - Real-time KPI metrics (Gross Revenue, Orders, Pending Allocations, Low Stock Alerts).
   - Interactive analytics powered by **Chart.js** (Daily revenue velocity, status breakdowns, TCG distribution).
   - Instant inline stock adjustments.
   - CSV export utilities for Orders, Products, and Inventory.

---

## Technology Stack

- **Backend**: Python 3.14, Django 6.1 (ORM, Auth, Templates, Signals, Database Transactions)
- **PDF Engine**: ReportLab 5.0
- **Frontend**: HTML5, CSS3, Modern JavaScript (Fetch API, DOM manipulation, Debouncing)
- **Analytics**: Chart.js
- **Database**: SQLite for development, configured for seamless switch to PostgreSQL in production

---

## Quick Start & Installation

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository and navigate into directory
cd novachrono

# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database & Run Migrations

```bash
python manage.py migrate
```

### 4. Seed Rich Collectibles Dataset

Run the automated seed command to populate 22 authentic TCG products, universes, categories, store settings, test accounts, and sample orders:

```bash
python manage.py seed_data
```

### 5. Start the Development Server

```bash
python manage.py runserver
```

Visit the application at: `http://127.0.0.1:8000/`

---

## Pre-Configured Demo Accounts

For testing, use the following accounts (or use the one-click quick fill buttons on the sign-in page):

| Role | Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin` | `admin123` | Full control, staff management, store settings, CSV exports |
| **Staff Member**| `staff_alex` | `staff123` | Product catalog, inventory adjustments, order fulfillment |
| **Buyer**       | `collector_ash` | `buyer123` | Cart, wishlist, checkout, orders history, PDF invoices |

---

## Project Structure

```
novachrono/
├── manage.py
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
│
├── config/
│   ├── settings.py           # Database abstraction, app registrations, static/media
│   ├── urls.py               # Main URL router with custom 404/403/500 handlers
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                 # CustomUser (roles), Address, Authentication, RBAC decorators
├── catalog/                  # TCG, Category, Product, Inventory, Review, Shop & Search APIs
├── cart/                     # Cart, CartItem, Voucher discounts, AJAX quantity management
├── wishlist/                 # Wishlist, WishlistItem, AJAX toggle, Guest login prompts
├── orders/                   # Orders, StatusHistory, Payment, Invoice, ReportLab PDF, Packing Slip
├── dashboard/                # Custom Admin Portal, Chart.js analytics, Staff/User management
├── core/                     # Seed data command, error handlers, global context processors
│
├── static/
│   ├── css/
│   │   ├── style.css         # Main design system, editorial layout, print stylesheet
│   │   └── dashboard.css     # Admin portal operations layout
│   └── js/
│       └── main.js           # Live search, quick view, cart/wishlist AJAX, toast system
│
└── templates/
    ├── base.html             # Sticky navbar, announcement ticker, user pill, footer
    ├── catalog/              # Home (editorial hero), Shop (filters), Product Detail
    ├── cart/                 # Cart review, free shipping threshold progress bar
    ├── wishlist/             # Wishlist grid and guest prompt
    ├── orders/               # Multi-step checkout, confirmation, history, detail, printable invoice, packing slip, shipping label
    ├── accounts/             # Login, register, profile, address book
    ├── dashboard/            # Operations overview, products, inventory, orders, staff, users, settings
    └── errors/               # Custom branded 404, 403, and 500 error pages
```

---

## Production PostgreSQL Migration

NovaChrono was structured to migrate from SQLite to PostgreSQL without code rewrites.

1. Install PostgreSQL database driver:
   ```bash
   pip install psycopg2-binary
   ```
2. Update your `.env` file:
   ```ini
   USE_POSTGRESQL=True
   DB_NAME=novachrono_db
   DB_USER=postgres
   DB_PASSWORD=your_secure_password
   DB_HOST=localhost
   DB_PORT=5432
   ```
3. Run migrations on the PostgreSQL database:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

---

## License & Compliance

NovaChrono is a demonstration trading card e-commerce architecture. Pokémon, One Piece, Yu-Gi-Oh!, Magic: The Gathering, Dragon Ball Super, and Gundam are registered trademarks of their respective copyright holders.
