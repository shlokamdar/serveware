from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Restaurant
from customer.models import Cart, Order
from restaurant.models import MenuItem, Table

STRONG_PASSWORD = "Str0ngPass!23"


def make_restaurant(username="resto"):
    admin = CustomUser.objects.create_user(
        username=username, password=STRONG_PASSWORD, user_type="restaurant",
        email=f"{username}@example.com",
    )
    return Restaurant.objects.create(
        restaurant_admin=admin,
        restaurant_name="Test Restaurant",
        restaurant_address="123 Main St",
        restaurant_pincode="560001",
        phone="9876543210",
        email=admin.email,
    )


class TableUpdateStatusTests(TestCase):
    """Regression tests for Table.update_table_status().

    The original implementation compared the string Order.status to the
    Table.BILL_PAID *boolean* field (`order.status == self.BILL_PAID`),
    so the "free the table once the bill is paid" branch could never
    fire, and it wrote the result to a non-existent `self.bill_paid`
    attribute instead of the real `BILL_PAID` field. These tests fail
    against that old behavior and pass against the fix.
    """

    def setUp(self):
        self.restaurant = make_restaurant()
        self.table = Table.objects.create(restaurant=self.restaurant, table_number="A1", seats=4)
        self.customer = CustomUser.objects.create_user(
            username="cust", password=STRONG_PASSWORD, user_type="customer",
        )

    def test_no_orders_leaves_table_free(self):
        self.table.update_table_status()

        self.assertFalse(self.table.is_occupied)
        self.assertFalse(self.table.BILL_PAID)

    def test_pending_order_keeps_table_occupied(self):
        cart = Cart.objects.create(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        Order.objects.create(cart=cart, user=self.customer, table=self.table, status=Order.PENDING)

        self.table.update_table_status()

        self.assertTrue(self.table.is_occupied)
        self.assertFalse(self.table.BILL_PAID)

    def test_bill_paid_order_frees_the_table(self):
        cart = Cart.objects.create(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        Order.objects.create(cart=cart, user=self.customer, table=self.table, status=Order.BILL_PAID)

        self.table.update_table_status()

        self.assertFalse(self.table.is_occupied)
        self.assertTrue(self.table.BILL_PAID)

    def test_one_bill_paid_order_among_several_still_frees_the_table(self):
        cart = Cart.objects.create(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        Order.objects.create(cart=cart, user=self.customer, table=self.table, status=Order.PENDING)
        Order.objects.create(cart=cart, user=self.customer, table=self.table, status=Order.BILL_PAID)

        self.table.update_table_status()

        self.assertFalse(self.table.is_occupied)
        self.assertTrue(self.table.BILL_PAID)


class AddTablesViewTests(TestCase):
    def setUp(self):
        self.restaurant = make_restaurant()
        self.client.login(username="resto", password=STRONG_PASSWORD)

    def test_add_table_creates_table_with_generated_qr_code(self):
        url = reverse("restaurant:add_tables")

        response = self.client.post(url, {"table_number": "A1", "seats": 4})

        table = Table.objects.get(restaurant=self.restaurant, table_number="A1")
        self.assertEqual(table.seats, 4)
        self.assertTrue(table.qr_code_image)
        self.assertRedirects(response, reverse("restaurant:view_tables"))

    def test_duplicate_table_number_is_rejected(self):
        Table.objects.create(restaurant=self.restaurant, table_number="A1", seats=4)
        url = reverse("restaurant:add_tables")

        response = self.client.post(url, {"table_number": "A1", "seats": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Table.objects.filter(restaurant=self.restaurant, table_number="A1").count(), 1)


class MenuItemCrudTests(TestCase):
    def setUp(self):
        self.restaurant = make_restaurant()

    def test_add_menu_item(self):
        url = reverse("restaurant:add-menu-item", args=[self.restaurant.qr_code])

        response = self.client.post(url, {
            "name": "Pizza", "description": "Cheesy", "price": "250.00", "category": "Main Course",
        })

        item = MenuItem.objects.get(restaurant=self.restaurant, name="Pizza")
        self.assertTrue(item.is_available)
        # Note: fetch_redirect_response=False - rendering the view_menu
        # template for a MenuItem with no image hits a separate,
        # pre-existing template bug (item.image.url on an empty
        # ImageField) that is out of scope for this change.
        self.assertRedirects(
            response, reverse("restaurant:view_menu", args=[self.restaurant.qr_code]),
            fetch_redirect_response=False,
        )

    def test_edit_menu_item_updates_fields(self):
        item = MenuItem.objects.create(
            restaurant=self.restaurant, name="Pizza", price=Decimal("250.00"), category="Main Course",
        )
        url = reverse("restaurant:edit-menu-item", args=[self.restaurant.qr_code, item.id])

        self.client.post(url, {
            "name": "Pizza Deluxe", "description": "", "price": "300.00", "category": "Main Course",
        })

        item.refresh_from_db()
        self.assertEqual(item.name, "Pizza Deluxe")
        self.assertEqual(item.price, Decimal("300.00"))

    def test_delete_menu_item_removes_it(self):
        item = MenuItem.objects.create(
            restaurant=self.restaurant, name="Pizza", price=Decimal("250.00"), category="Main Course",
        )
        url = reverse("restaurant:delete-menu-item", args=[self.restaurant.qr_code, item.id])

        self.client.post(url)

        self.assertFalse(MenuItem.objects.filter(id=item.id).exists())
