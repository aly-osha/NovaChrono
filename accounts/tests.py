from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Address, User
from orders.models import Order


class AddressManagementAndIntegrityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer@example.com",
            password="StrongPassword123!",
            name="Buyer One",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="other@example.com",
            password="StrongPassword123!",
            name="Other Buyer",
        )
        self.client.force_login(self.user)

    def _create_address(self, user=None, line1="100 Main St", is_default=False):
        return Address.objects.create(
            buyer=user or self.user,
            line1=line1,
            line2="Suite 2",
            city="Mumbai",
            state="Maharashtra",
            postal_code="400001",
            country="India",
            is_default=is_default,
        )

    def test_delete_unused_address(self):
        addr = self._create_address(line1="Unused Lane", is_default=False)
        resp = self.client.post(reverse("address_delete", args=[addr.pk]))
        self.assertRedirects(resp, reverse("address_list"))
        self.assertFalse(Address.objects.filter(pk=addr.pk).exists())

    def test_delete_address_associated_with_single_order(self):
        addr = self._create_address(line1="Order St 1", is_default=True)
        order = Order.objects.create(
            buyer=self.user,
            shipping_address=addr,
            total_amount=Decimal("250.00"),
        )
        resp = self.client.post(reverse("address_delete", args=[addr.pk]))
        self.assertRedirects(resp, reverse("address_list"))
        self.assertFalse(Address.objects.filter(pk=addr.pk).exists())

        order.refresh_from_db()
        self.assertIsNone(order.shipping_address)
        self.assertEqual(order.shipping_address_line1, "Order St 1")

    def test_delete_address_associated_with_multiple_orders(self):
        addr = self._create_address(line1="Multi Order Blvd", is_default=True)
        o1 = Order.objects.create(
            buyer=self.user,
            shipping_address=addr,
            total_amount=Decimal("100.00"),
        )
        o2 = Order.objects.create(
            buyer=self.user,
            shipping_address=addr,
            total_amount=Decimal("200.00"),
        )
        resp = self.client.post(reverse("address_delete", args=[addr.pk]))
        self.assertRedirects(resp, reverse("address_list"))
        self.assertFalse(Address.objects.filter(pk=addr.pk).exists())

        for order in (o1, o2):
            order.refresh_from_db()
            self.assertIsNone(order.shipping_address)
            self.assertEqual(order.shipping_address_line1, "Multi Order Blvd")

    def test_delete_default_address_assigns_another_default(self):
        default_addr = self._create_address(line1="Old Default", is_default=True)
        backup_addr = self._create_address(line1="New Default", is_default=False)

        resp = self.client.post(reverse("address_delete", args=[default_addr.pk]))
        self.assertRedirects(resp, reverse("address_list"))
        self.assertFalse(Address.objects.filter(pk=default_addr.pk).exists())

        backup_addr.refresh_from_db()
        self.assertTrue(backup_addr.is_default)

    def test_delete_only_saved_address(self):
        only_addr = self._create_address(line1="Only Address", is_default=True)
        resp = self.client.post(reverse("address_delete", args=[only_addr.pk]))
        self.assertRedirects(resp, reverse("address_list"))
        self.assertEqual(self.user.addresses.count(), 0)

    def test_existing_orders_and_invoices_retain_original_address_on_edit_and_delete(self):
        addr = self._create_address(line1="Original Invoice Rd", is_default=True)
        order = Order.objects.create(
            buyer=self.user,
            shipping_address=addr,
            total_amount=Decimal("999.00"),
        )

        # Edit the saved address; order snapshot must not change.
        self.client.post(
            reverse("address_edit", args=[addr.pk]),
            {
                "line1": "Edited Street",
                "line2": "Floor 9",
                "city": "Pune",
                "state": "Maharashtra",
                "postal_code": "411001",
                "country": "India",
                "is_default": "on",
            },
        )
        order.refresh_from_db()
        self.assertEqual(order.shipping_address_line1, "Original Invoice Rd")
        self.assertEqual(order.shipping_city, "Mumbai")

        # Delete the saved address; order history, detail, and PDF invoice still work.
        self.client.post(reverse("address_delete", args=[addr.pk]))
        order.refresh_from_db()
        self.assertIsNone(order.shipping_address)
        self.assertEqual(order.shipping_address_line1, "Original Invoice Rd")

        list_resp = self.client.get(reverse("order_list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, "Original Invoice Rd")

        detail_resp = self.client.get(reverse("order_detail", args=[order.pk]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Original Invoice Rd")

        invoice_resp = self.client.get(reverse("order_invoice_pdf", args=[order.pk]))
        self.assertEqual(invoice_resp.status_code, 200)
        self.assertEqual(invoice_resp["Content-Type"], "application/pdf")

    def test_customer_cannot_manipulate_other_customers_address(self):
        other_addr = self._create_address(user=self.other_user, line1="Private St", is_default=True)

        edit_resp = self.client.post(
            reverse("address_edit", args=[other_addr.pk]),
            {
                "line1": "Hacked St",
                "line2": "",
                "city": "Delhi",
                "state": "Delhi",
                "postal_code": "110001",
                "country": "India",
            },
        )
        self.assertEqual(edit_resp.status_code, 404)

        del_resp = self.client.post(reverse("address_delete", args=[other_addr.pk]))
        self.assertEqual(del_resp.status_code, 404)

        other_addr.refresh_from_db()
        self.assertEqual(other_addr.line1, "Private St")

    def test_address_delete_requires_post(self):
        addr = self._create_address(line1="Method Guard St")
        resp = self.client.get(reverse("address_delete", args=[addr.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Address.objects.filter(pk=addr.pk).exists())


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            username="admin@example.com",
            password="AdminPassword123!",
            name="Admin User",
        )
        self.customer = User.objects.create_user(
            email="cust@example.com",
            username="cust@example.com",
            password="CustPassword123!",
            name="Customer User",
        )

    def test_non_admin_cannot_access_user_management(self):
        self.client.force_login(self.customer)
        resp = self.client.get(reverse("admin_user_list"))
        self.assertEqual(resp.status_code, 302)

    def test_admin_can_list_and_search_users(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("admin_user_list"), {"q": "cust@example.com"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "cust@example.com")
        self.assertEqual(list(resp.context["users"]), [self.customer])

    def test_admin_can_toggle_customer_status_and_role(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("admin_user_toggle_status", args=[self.customer.pk]))
        self.assertRedirects(resp, reverse("admin_user_list"))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "suspended")

        resp2 = self.client.post(reverse("admin_user_toggle_role", args=[self.customer.pk]))
        self.assertRedirects(resp2, reverse("admin_user_list"))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_superuser)

    def test_admin_cannot_suspend_or_demote_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("admin_user_toggle_status", args=[self.admin.pk]))
        self.client.post(reverse("admin_user_toggle_role", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.status, "active")
        self.assertTrue(self.admin.is_superuser)

    def test_admin_user_detail_edit(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_user_detail", args=[self.customer.pk]),
            {
                "name": "Updated Customer",
                "phone": "9876543210",
                "status": "inactive",
            },
        )
        self.assertRedirects(resp, reverse("admin_user_detail", args=[self.customer.pk]))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Updated Customer")
        self.assertEqual(self.customer.phone, "9876543210")
        self.assertEqual(self.customer.status, "inactive")
