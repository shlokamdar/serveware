import json

from django.contrib.auth import get_user_model
from django.urls import resolve, reverse

from customer.models import Order
from restaurant.models import MenuItem
from testutils import (
    PASSWORD,
    ServeWareTestCase,
    make_customer,
    make_menu_item,
    make_restaurant_owner,
    make_table,
)


class MenuAuthorizationTests(ServeWareTestCase):
    def setUp(self):
        self.owner, self.restaurant = make_restaurant_owner()
        self.other_owner, _ = make_restaurant_owner()
        self.item = make_menu_item(self.restaurant)
        self.code = self.restaurant.qr_code

    def test_anonymous_cannot_add_menu_item(self):
        response = self.client.get(reverse("restaurant:add-menu-item", args=[self.code]))
        self.assertEqual(response.status_code, 302)

    def test_customer_is_forbidden(self):
        customer = make_customer()
        self.client.login(username=customer.username, password=PASSWORD)
        response = self.client.get(reverse("restaurant:add-menu-item", args=[self.code]))
        self.assertEqual(response.status_code, 403)

    def test_other_restaurant_cannot_edit_item(self):
        self.client.login(username=self.other_owner.username, password=PASSWORD)
        response = self.client.get(reverse("restaurant:edit-menu-item", args=[self.code, self.item.id]))
        self.assertEqual(response.status_code, 404)

    def test_delete_rejects_get(self):
        self.client.login(username=self.owner.username, password=PASSWORD)
        response = self.client.get(reverse("restaurant:delete-menu-item", args=[self.code, self.item.id]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(MenuItem.objects.filter(id=self.item.id).exists())

    def test_owner_can_delete_with_post(self):
        self.client.login(username=self.owner.username, password=PASSWORD)
        self.client.post(reverse("restaurant:delete-menu-item", args=[self.code, self.item.id]))
        self.assertFalse(MenuItem.objects.filter(id=self.item.id).exists())


class TableModelTests(ServeWareTestCase):
    def setUp(self):
        _, self.restaurant = make_restaurant_owner()
        self.table = make_table(self.restaurant)

    def test_qr_points_to_a_real_customer_route(self):
        match = resolve(self.table.menu_path())
        self.assertEqual(match.view_name, "customer:view_menu")

    def test_qr_image_generated_once(self):
        self.assertTrue(self.table.qr_code_image)
        first = self.table.qr_code_image.name
        self.table.seats = 6
        self.table.save()
        self.assertEqual(self.table.qr_code_image.name, first)

    def test_table_freed_after_bill_paid(self):
        customer = make_customer()
        order = Order.objects.create(user=customer, table=self.table, status="Pending")
        self.table.update_table_status()
        self.table.refresh_from_db()
        self.assertTrue(self.table.is_occupied)
        order.status = "Bill_Paid"
        order.save()
        self.table.refresh_from_db()
        self.assertFalse(self.table.is_occupied)
        self.assertTrue(self.table.BILL_PAID)


class OrderStatusApiTests(ServeWareTestCase):
    def setUp(self):
        self.owner, restaurant = make_restaurant_owner()
        table = make_table(restaurant)
        self.order = Order.objects.create(user=make_customer(), table=table, status="Pending")
        self.url = reverse("restaurant:update_order_status", args=[self.order.id])
        self.client.login(username=self.owner.username, password=PASSWORD)

    def test_valid_status_update(self):
        self.client.post(self.url, json.dumps({"status": "Completed"}), content_type="application/json")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "Completed")

    def test_invalid_status_rejected(self):
        response = self.client.post(self.url, json.dumps({"status": "Hacked"}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "Pending")


class AdminSearchTests(ServeWareTestCase):
    def test_table_admin_search_does_not_crash(self):
        admin = get_user_model().objects.create_superuser(
            "admin", "admin@test.local", PASSWORD, user_type="restaurant"
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("admin:restaurant_table_changelist") + "?q=Test")
        self.assertEqual(response.status_code, 200)
