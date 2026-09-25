from decimal import Decimal
import json

from django.test import tag
from django.urls import reverse

from customer.models import Cart, CartItem, Order
from testutils import (
    PASSWORD,
    ServeWareTestCase,
    make_customer,
    make_menu_item,
    make_restaurant_owner,
    make_table,
)


class CartModelTests(ServeWareTestCase):
    def test_cart_total_is_sum_of_line_items(self):
        _, restaurant = make_restaurant_owner()
        table = make_table(restaurant)
        cart = Cart.objects.create(user=make_customer(), restaurant=restaurant, table_code=table.table_code)
        CartItem.objects.create(cart=cart, menu_item=make_menu_item(restaurant, "A", "249.00"), quantity=2)
        CartItem.objects.create(cart=cart, menu_item=make_menu_item(restaurant, "B", "100.00"), quantity=1)
        self.assertEqual(cart.total_price(), Decimal("598.00"))


class CartViewTests(ServeWareTestCase):
    def setUp(self):
        _, self.restaurant = make_restaurant_owner()
        self.table = make_table(self.restaurant)
        self.item = make_menu_item(self.restaurant)
        self.customer = make_customer()
        self.args = [self.restaurant.qr_code, self.table.table_code]

    def _add(self):
        return self.client.post(reverse("customer:add_to_cart", args=[*self.args, self.item.id]))

    def test_anonymous_add_to_cart_redirects_to_signin(self):
        response = self._add()
        self.assertEqual(response.status_code, 302)
        self.assertIn("signin", response["Location"])

    def test_add_twice_increments_quantity(self):
        self.client.login(username=self.customer.username, password=PASSWORD)
        self._add()
        self._add()
        self.assertEqual(CartItem.objects.get(menu_item=self.item, cart__user=self.customer).quantity, 2)

    def test_cannot_delete_another_users_cart_item(self):
        other = make_customer()
        cart = Cart.objects.create(user=other, restaurant=self.restaurant, table_code=self.table.table_code)
        line = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        self.client.login(username=self.customer.username, password=PASSWORD)
        response = self.client.post(reverse("customer:delete_cart_item", args=[line.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(id=line.id).exists())

    def test_menu_loads_for_valid_codes(self):
        self.client.login(username=self.customer.username, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("customer:view_menu", args=self.args)).status_code, 200)

    def test_menu_404_for_unknown_restaurant(self):
        self.client.login(username=self.customer.username, password=PASSWORD)
        response = self.client.get(reverse("customer:view_menu", args=["nope", self.table.table_code]))
        self.assertEqual(response.status_code, 404)


@tag("integration")
class OrderFlowIntegrationTest(ServeWareTestCase):
    """End-to-end: customer orders at a table, restaurant sees and closes it."""

    def test_customer_order_to_bill_paid(self):
        owner, restaurant = make_restaurant_owner()
        table = make_table(restaurant)
        item = make_menu_item(restaurant)
        customer = make_customer()
        args = [restaurant.qr_code, table.table_code]

        self.client.login(username=customer.username, password=PASSWORD)
        self.client.post(reverse("customer:add_to_cart", args=[*args, item.id]))
        self.client.post(reverse("customer:place_order", args=args))

        order = Order.objects.get(user=customer)
        self.assertEqual(order.status, "Pending")
        table.refresh_from_db()
        self.assertTrue(table.is_occupied)
        self.assertEqual(Cart.objects.filter(user=customer, is_active=True).count(), 1)

        self.client.logout()
        self.client.login(username=owner.username, password=PASSWORD)
        page = self.client.get(reverse("restaurant:view_orders"))
        self.assertContains(page, customer.username)

        self.client.post(
            reverse("restaurant:update_order_status", args=[order.id]),
            json.dumps({"status": "Bill_Paid"}),
            content_type="application/json",
        )
        table.refresh_from_db()
        self.assertFalse(table.is_occupied)
