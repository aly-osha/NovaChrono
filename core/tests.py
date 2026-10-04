from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from products.models import Game, Category, Set, Product, SingleCardDetail, SealedPack
from cart.models import Cart, CartItem
from wishlists.models import Wishlist, WishlistItem
from notifications.models import Notification
from notifications.monitoring import run_monitoring
from orders.models import Order, OrderItem, Payment, CASH_ON_DELIVERY
from accounts.models import Address
from certificates.models import AuthenticityCertificate
from reviews.models import Review
from analytics.models import ActivityLog

User = get_user_model()


class NovaChronoIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.buyer = User.objects.create_user(
            username="buyer@example.com",
            email="buyer@example.com",
            password="Password123!",
            name="Ash Ketchum",
            role="buyer",
        )
        self.admin = User.objects.create_user(
            username="admin@novachrono.com",
            email="admin@novachrono.com",
            password="AdminPassword123!",
            name="NovaChrono Admin",
            role="admin",
        )

        # Address
        self.address = Address.objects.create(
            buyer=self.buyer,
            line1="Pallet Town 1",
            city="Kanto",
            state="Indigo",
            postal_code="12345",
            country="Japan",
            is_default=True,
        )

        # Taxonomy
        self.game = Game.objects.create(name="Pokemon TCG")
        self.category = Category.objects.create(name="Single Cards")
        self.set_obj = Set.objects.create(game=self.game, name="151 Expansion")

        # Products
        self.product1 = Product.objects.create(
            name="Charizard ex",
            description="Special Illustration Rare Charizard",
            price=Decimal("15000.00"),
            stock=5,
            product_type="single_card",
            game=self.game,
            set=self.set_obj,
            category=self.category,
            is_active=True,
        )
        self.single_detail = SingleCardDetail.objects.create(
            product=self.product1,
            rarity="Special Illustration Rare",
            language="English",
            condition="near_mint",
        )

        self.product2 = Product.objects.create(
            name="Booster Box 151",
            description="Factory sealed booster display",
            price=Decimal("8500.00"),
            stock=10,
            product_type="sealed",
            game=self.game,
            set=self.set_obj,
            category=self.category,
            is_active=True,
        )
        self.sealed_pack = SealedPack.objects.create(product=self.product2)

    # 1. Storefront & Catalogue
    def test_homepage_and_catalogue_rendering(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Charizard ex")
        self.assertContains(response, "Booster Box 151")

        response = self.client.get(reverse("catalogue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Charizard ex")

        # Search by name
        response = self.client.get(reverse("catalogue") + "?q=Charizard")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Charizard ex")
        self.assertNotContains(response, "Booster Box 151")

        # Filter by Game
        response = self.client.get(reverse("catalogue") + f"?game={self.game.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Charizard ex")

    def test_api_sets_endpoint(self):
        response = self.client.get(reverse("api_sets") + f"?game={self.game.pk}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "151 Expansion")

    # 2. Authentication & User Profile
    def test_user_auth_and_profile_flow(self):
        # Register new user
        reg_response = self.client.post(reverse("register"), data={
            "name": "Misty Waterflower",
            "email": "misty@cerulean.com",
            "password1": "Starmie123!",
            "password2": "Starmie123!",
            "phone": "9876543210",
        })
        self.assertRedirects(reg_response, reverse("login"))
        new_user = User.objects.get(email="misty@cerulean.com")
        self.assertEqual(new_user.name, "Misty Waterflower")

        # Login
        login_response = self.client.post(reverse("login"), data={
            "email": "misty@cerulean.com",
            "password": "Starmie123!",
        })
        self.assertRedirects(login_response, reverse("home"))

        # Profile update
        prof_response = self.client.post(reverse("profile"), data={
            "name": "Misty Gym Leader",
            "email": "misty@cerulean.com",
            "phone": "9876543219",
        })
        self.assertRedirects(prof_response, reverse("profile"))
        new_user.refresh_from_db()
        self.assertEqual(new_user.name, "Misty Gym Leader")

        # Logout
        logout_response = self.client.get(reverse("logout"))
        self.assertRedirects(logout_response, reverse("home"))

    # 3. Address Management
    def test_address_management(self):
        self.client.login(username="buyer@example.com", password="Password123!")

        # Create address
        response = self.client.post(reverse("address_create"), data={
            "line1": "Viridian City 4",
            "line2": "Apt 2B",
            "city": "Viridian",
            "state": "Kanto",
            "postal_code": "54321",
            "country": "Japan",
            "is_default": True,
        })
        self.assertRedirects(response, reverse("address_list"))

        new_addr = Address.objects.get(line1="Viridian City 4")
        self.assertTrue(new_addr.is_default)
        self.address.refresh_from_db()
        self.assertFalse(self.address.is_default)  # Previous default unset

        # Edit address
        response = self.client.post(reverse("address_edit", args=[new_addr.pk]), data={
            "line1": "Viridian City 40",
            "city": "Viridian",
            "state": "Kanto",
            "postal_code": "54321",
            "country": "Japan",
            "is_default": True,
        })
        self.assertRedirects(response, reverse("address_list"))
        new_addr.refresh_from_db()
        self.assertEqual(new_addr.line1, "Viridian City 40")

        # Delete address
        response = self.client.post(reverse("address_delete", args=[new_addr.pk]))
        self.assertRedirects(response, reverse("address_list"))
        self.assertFalse(Address.objects.filter(pk=new_addr.pk).exists())

    # 4. Cart Workflow
    def test_cart_workflow_and_update(self):
        self.client.login(username="buyer@example.com", password="Password123!")

        # Add to cart
        response = self.client.get(reverse("cart_add", args=[self.product1.pk]) + "?qty=2")
        self.assertRedirects(response, reverse("cart"))

        cart = Cart.objects.get(buyer=self.buyer)
        item = cart.items.first()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(cart.subtotal, Decimal("30000.00"))

        # Update cart quantity using item.pk
        response = self.client.post(
            reverse("cart_update", args=[item.pk]),
            data={"quantity": 3},
        )
        self.assertRedirects(response, reverse("cart"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

        # Quantity capped at stock (stock is 5)
        response = self.client.post(
            reverse("cart_update", args=[item.pk]),
            data={"quantity": 99},
        )
        self.assertRedirects(response, reverse("cart"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

        # Remove from cart
        response = self.client.post(reverse("cart_remove", args=[self.product1.pk]))
        self.assertRedirects(response, reverse("cart"))
        self.assertEqual(cart.items.count(), 0)

    # 5. Wishlists & Monitoring
    def test_wishlist_monitoring_and_transfer_to_cart(self):
        self.client.login(username="buyer@example.com", password="Password123!")

        # Add to wishlist
        response = self.client.get(reverse("wishlist_add", args=[self.product1.pk]))
        self.assertRedirects(response, reverse("product_detail", args=[self.product1.pk]))

        wl = Wishlist.objects.get(buyer=self.buyer)
        wl_item = wl.items.get(product=self.product1)
        self.assertEqual(wl_item.added_price, Decimal("15000.00"))
        self.assertFalse(wl_item.was_out_of_stock)

        # Price drop trigger
        self.product1.price = Decimal("13000.00")
        self.product1.save()

        checked, created = run_monitoring()
        self.assertGreater(len(created), 0)
        notif = Notification.objects.filter(buyer=self.buyer, notification_type="price_drop").first()
        self.assertIsNotNone(notif)
        self.assertIn("Price drop", notif.title)

        # Move to cart
        response = self.client.get(reverse("wishlist_to_cart", args=[self.product1.pk]))
        self.assertRedirects(response, reverse("cart"))
        self.assertEqual(wl.items.filter(product=self.product1).count(), 0)
        cart = Cart.objects.get(buyer=self.buyer)
        self.assertEqual(cart.items.filter(product=self.product1).count(), 1)

    # 6. Notifications
    def test_notifications_flow(self):
        self.client.login(username="buyer@example.com", password="Password123!")
        notif = Notification.objects.create(
            buyer=self.buyer,
            product=self.product1,
            notification_type="price_drop",
            title="Price drop on Charizard ex",
            message="Now at ₹13000",
            is_read=False,
        )

        response = self.client.get(reverse("notification_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price drop on Charizard ex")

        # Mark single as read
        response = self.client.post(reverse("notification_mark_read", args=[notif.pk]))
        self.assertRedirects(response, reverse("notification_list"))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

        # Mark all as read
        Notification.objects.create(
            buyer=self.buyer,
            product=self.product2,
            notification_type="restock",
            title="Booster Box Restocked",
            message="Now available",
            is_read=False,
        )
        response = self.client.post(reverse("notification_mark_all"))
        self.assertRedirects(response, reverse("notification_list"))
        self.assertEqual(Notification.objects.filter(buyer=self.buyer, is_read=False).count(), 0)

    # 7. Checkout Page Form & Order Confirmation Flow
    def test_checkout_page_renders_form_and_submit_button(self):
        self.client.login(username="buyer@example.com", password="Password123!")
        cart, _ = Cart.objects.get_or_create(buyer=self.buyer)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=1)

        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)
        # Verify form exists with action and submit button
        self.assertContains(response, 'action="/checkout/"')
        self.assertContains(response, 'type="submit"')
        self.assertContains(response, "Place Order")

    def test_checkout_creates_order_and_accurate_payment(self):
        self.client.login(username="buyer@example.com", password="Password123!")

        # Put item in cart
        cart, _ = Cart.objects.get_or_create(buyer=self.buyer)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=2)

        # POST checkout with COD
        response = self.client.post(reverse("checkout"), data={
            "address": self.address.pk,
            "payment_method": CASH_ON_DELIVERY,
        })
        order = Order.objects.filter(buyer=self.buyer).first()
        self.assertIsNotNone(order)
        self.assertRedirects(response, reverse("order_detail", args=[order.pk]))

        # Verify order details
        self.assertEqual(order.total_amount, Decimal("30000.00"))
        self.assertEqual(order.shipping_name, "Ash Ketchum")
        self.assertEqual(order.shipping_city, "Kanto")

        # Verify order_detail confirmation view renders correctly
        detail_response = self.client.get(reverse("order_detail", args=[order.pk]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, f"Order #{order.pk}")
        self.assertContains(detail_response, "Pallet Town 1")
        self.assertContains(detail_response, "Charizard ex")

        # Verify stock decremented (5 - 2 = 3)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 3)

        # Verify Payment amount is NOT 0.00
        payment = order.payment
        self.assertEqual(payment.amount, Decimal("30000.00"))
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.method, "cod")

        # Test admin order status update to delivered settles COD payment
        self.client.login(username="admin@novachrono.com", password="AdminPassword123!")
        response = self.client.post(reverse("admin_order_detail", args=[order.pk]), data={
            "status": "delivered",
        })
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, "delivered")
        self.assertEqual(payment.status, "success")
        self.assertIsNotNone(payment.paid_at)

    def test_checkout_insufficient_stock_prevents_order(self):
        self.client.login(username="buyer@example.com", password="Password123!")
        cart, _ = Cart.objects.get_or_create(buyer=self.buyer)
        # Attempt to order 10 when stock is only 5
        CartItem.objects.create(cart=cart, product=self.product1, quantity=10)

        response = self.client.post(reverse("checkout"), data={
            "address": self.address.pk,
            "payment_method": "card",
        })
        # Should redirect back to cart without creating order
        self.assertRedirects(response, reverse("cart"))
        self.assertEqual(Order.objects.filter(buyer=self.buyer).count(), 0)

    # 8. Reviews Flow
    def test_reviews_verified_purchase_and_admin_moderation(self):
        self.client.login(username="buyer@example.com", password="Password123!")

        # Unpurchased review should fail
        response = self.client.post(reverse("add_review", args=[self.product1.pk]), data={
            "rating": 5,
            "comment": "Awesome card!",
        })
        self.assertRedirects(response, reverse("product_detail", args=[self.product1.pk]))
        self.assertEqual(Review.objects.count(), 0)

        # Create verified purchase order
        order = Order.objects.create(
            buyer=self.buyer,
            shipping_address=self.address,
            total_amount=Decimal("15000.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=1,
            unit_price=self.product1.price,
            subtotal=self.product1.price,
        )

        # Now submit review
        response = self.client.post(reverse("add_review", args=[self.product1.pk]), data={
            "rating": 5,
            "comment": "Authentic grail! Beautiful texture.",
        })
        self.assertRedirects(response, reverse("product_detail", args=[self.product1.pk]))
        review = Review.objects.get(product=self.product1, buyer=self.buyer)
        self.assertTrue(review.is_verified_purchase)
        self.assertEqual(review.rating, 5)

        # Admin moderates review
        self.client.login(username="admin@novachrono.com", password="AdminPassword123!")
        response = self.client.post(reverse("admin_review_detail", args=[review.pk]), data={
            "action": "hide",
        })
        self.assertRedirects(response, reverse("admin_review_detail", args=[review.pk]))
        review.refresh_from_db()
        self.assertFalse(review.is_approved)

    # 9. Authenticity Certificate Flow
    def test_authenticity_certificate_issue_and_revoke(self):
        # Admin creates certificate
        self.client.login(username="admin@novachrono.com", password="AdminPassword123!")
        response = self.client.post(reverse("admin_certificate_create", args=[self.product1.pk]))
        self.assertRedirects(response, reverse("admin_certificate_list"))

        cert = AuthenticityCertificate.objects.filter(product=self.product1, is_active=True).first()
        self.assertIsNotNone(cert)
        self.assertTrue(cert.is_active)
        self.assertEqual(cert.status, "valid")

        # Public verification
        response = self.client.get(reverse("verify_certificate") + f"?code={cert.verification_code}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Certificate Valid — Authenticity Confirmed")

        # Admin revokes certificate
        response = self.client.get(reverse("admin_certificate_revoke", args=[cert.pk]))
        self.assertRedirects(response, reverse("admin_certificate_list"))
        cert.refresh_from_db()
        self.assertFalse(cert.is_active)
        self.assertEqual(cert.status, "revoked")

    # 10. Admin Taxonomy, Products & Inventory
    def test_admin_taxonomy_and_inventory(self):
        self.client.login(username="admin@novachrono.com", password="AdminPassword123!")

        # Create Game
        response = self.client.post(reverse("admin_game_create"), data={"name": "One Piece Card Game"})
        self.assertRedirects(response, reverse("admin_game_list"))
        self.assertTrue(Game.objects.filter(name="One Piece Card Game").exists())

        # Create Category
        response = self.client.post(reverse("admin_category_create"), data={
            "name": "Graded Slabs",
            "description": "PSA and BGS graded cards",
        })
        self.assertRedirects(response, reverse("admin_category_list"))
        self.assertTrue(Category.objects.filter(name="Graded Slabs").exists())

        # Update inventory stock
        response = self.client.post(reverse("admin_inventory_update", args=[self.product1.pk]), data={
            "stock": 25,
        })
        self.assertRedirects(response, reverse("admin_inventory"))
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 25)

        # Update product price & details
        response = self.client.post(reverse("admin_product_edit", args=[self.product1.pk]), data={
            "name": self.product1.name,
            "description": "Updated description",
            "price": "14500.00",
            "stock": 25,
            "game_id": self.game.pk,
            "set_id": self.set_obj.pk,
            "category_id": self.category.pk,
            "product_type": "single_card",
            "rarity": "Special Illustration Rare",
            "condition": "near_mint",
            "language": "English",
        })
        self.assertRedirects(response, reverse("admin_product_list"))
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.price, Decimal("14500.00"))

        # Delete product
        del_target = Product.objects.create(
            name="Temporary Test Card",
            description="To be deleted",
            price=Decimal("999.00"),
            stock=5,
            product_type="sealed",
            game=self.game,
            category=self.category,
        )
        # GET confirm page
        get_resp = self.client.get(reverse("admin_product_delete", args=[del_target.pk]))
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, "Temporary Test Card")

        # POST delete
        post_resp = self.client.post(reverse("admin_product_delete", args=[del_target.pk]))
        self.assertRedirects(post_resp, reverse("admin_product_list"))
        self.assertFalse(Product.objects.filter(pk=del_target.pk).exists())

    # 11. Admin RBAC Protection
    def test_admin_rbac_protection(self):
        self.client.login(username="buyer@example.com", password="Password123!")

        endpoints = [
            reverse("admin_dashboard"),
            reverse("admin_product_list"),
            reverse("admin_product_delete", args=[self.product1.pk]),
            reverse("admin_order_list"),
            reverse("admin_review_list"),
            reverse("admin_certificate_list"),
            reverse("admin_inventory"),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200, f"Buyer accessed admin endpoint: {url}")

    # 12. Invoice PDF Generation & Download
    def test_order_invoice_pdf_download(self):
        # Create an order with items and payment
        order = Order.objects.create(
            buyer=self.buyer,
            shipping_address=self.address,
            total_amount=Decimal("15000.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=1,
            unit_price=self.product1.price,
            subtotal=self.product1.price,
        )
        Payment.objects.create(
            order=order,
            method="card",
            amount=Decimal("15000.00"),
            status="success",
            transaction_ref="TXN-INVOICE-TEST-1",
        )

        # Buyer downloads invoice
        self.client.login(username="buyer@example.com", password="Password123!")
        response = self.client.get(reverse("order_invoice_pdf", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn(f"Invoice-NC-{order.pk:05d}.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

        # Inline preview
        response = self.client.get(reverse("order_invoice_pdf", args=[order.pk]) + "?view=inline")
        self.assertEqual(response.status_code, 200)
        self.assertIn("inline;", response["Content-Disposition"])

        # Admin downloads buyer's invoice
        self.client.login(username="admin@novachrono.com", password="AdminPassword123!")
        response = self.client.get(reverse("order_invoice_pdf", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Another buyer cannot access this order's invoice
        other_buyer = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="OtherPassword123!",
            role="buyer",
        )
        self.client.login(username="other@example.com", password="OtherPassword123!")
        response = self.client.get(reverse("order_invoice_pdf", args=[order.pk]))
        self.assertEqual(response.status_code, 404)

