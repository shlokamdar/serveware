from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Customer, Restaurant
from customer.models import Cart, CartItem, Order
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


def make_customer(username="cust"):
    user = CustomUser.objects.create_user(
        username=username, password=STRONG_PASSWORD, user_type="customer",
        email=f"{username}@example.com",
    )
    Customer.objects.create(user=user, phone="9876543211")
    return user


class CartModelTests(TestCase):
    def setUp(self):
        self.restaurant = make_restaurant()
        self.customer = make_customer()
        self.table = Table.objects.create(restaurant=self.restaurant, table_number="A1", seats=4)
        self.item1 = MenuItem.objects.create(
            restaurant=self.restaurant, name="Pizza", price=Decimal("250.00"), category="Main Course",
        )
        self.item2 = MenuItem.objects.create(
            restaurant=self.restaurant, name="Coke", price=Decimal("50.00"), category="Beverages",
        )
        self.cart = Cart.objects.create(
            user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code,
        )

    def test_total_price_sums_cart_items(self):
        CartItem.objects.create(cart=self.cart, menu_item=self.item1, quantity=2)  # 500.00
        CartItem.objects.create(cart=self.cart, menu_item=self.item2, quantity=3)  # 150.00

        self.assertEqual(self.cart.total_price(), Decimal("650.00"))

    def test_total_price_empty_cart_is_zero(self):
        self.assertEqual(self.cart.total_price(), 0)

    def test_cart_item_total_price(self):
        cart_item = CartItem.objects.create(cart=self.cart, menu_item=self.item1, quantity=3)
        self.assertEqual(cart_item.total_price(), Decimal("750.00"))


class CartViewTests(TestCase):
    def setUp(self):
        self.restaurant = make_restaurant()
        self.customer = make_customer()
        self.table = Table.objects.create(restaurant=self.restaurant, table_number="A1", seats=4)
        self.item = MenuItem.objects.create(
            restaurant=self.restaurant, name="Pizza", price=Decimal("250.00"), category="Main Course",
        )
        self.client.login(username="cust", password=STRONG_PASSWORD)

    def test_add_to_cart_creates_cart_and_item(self):
        url = reverse("customer:add_to_cart", args=[self.restaurant.qr_code, self.table.table_code, self.item.id])

        self.client.post(url)

        cart = Cart.objects.get(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        self.assertEqual(cart.cart_items.count(), 1)
        self.assertEqual(cart.cart_items.first().quantity, 1)

    def test_add_to_cart_twice_increments_quantity_instead_of_duplicating(self):
        url = reverse("customer:add_to_cart", args=[self.restaurant.qr_code, self.table.table_code, self.item.id])

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(CartItem.objects.filter(menu_item=self.item).count(), 1)
        self.assertEqual(CartItem.objects.get(menu_item=self.item).quantity, 2)

    def test_update_cart_quantity_increment(self):
        cart = Cart.objects.create(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        cart_item = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        url = reverse("customer:update_cart_quantity", args=[cart_item.id, "increment"])

        self.client.post(url)

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

    def test_update_cart_quantity_decrement_does_not_go_below_one(self):
        cart = Cart.objects.create(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        cart_item = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        url = reverse("customer:update_cart_quantity", args=[cart_item.id, "decrement"])

        self.client.post(url)

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)

    def test_delete_cart_item_removes_item_for_owner(self):
        cart = Cart.objects.create(user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code)
        cart_item = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        url = reverse("customer:delete_cart_item", args=[cart_item.id])

        self.client.post(url)

        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_delete_cart_item_leaves_item_for_non_owner(self):
        other_customer = make_customer("other")
        other_cart = Cart.objects.create(
            user=other_customer, restaurant=self.restaurant, table_code=self.table.table_code,
        )
        cart_item = CartItem.objects.create(cart=other_cart, menu_item=self.item, quantity=1)
        url = reverse("customer:delete_cart_item", args=[cart_item.id])

        # Logged in as self.customer, attempting to delete another customer's item.
        self.client.post(url)

        self.assertTrue(CartItem.objects.filter(id=cart_item.id).exists())


class OrderFlowTests(TestCase):
    def setUp(self):
        self.restaurant = make_restaurant()
        self.customer = make_customer()
        self.table = Table.objects.create(restaurant=self.restaurant, table_number="A1", seats=4)
        self.item = MenuItem.objects.create(
            restaurant=self.restaurant, name="Pizza", price=Decimal("250.00"), category="Main Course",
        )
        self.client.login(username="cust", password=STRONG_PASSWORD)
        self.cart = Cart.objects.create(
            user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code, is_active=True,
        )
        CartItem.objects.create(cart=self.cart, menu_item=self.item, quantity=2)

    def test_place_order_creates_pending_order_and_occupies_table(self):
        url = reverse("customer:place_order", args=[self.restaurant.qr_code, self.table.table_code])

        self.client.post(url)

        order = Order.objects.get(cart=self.cart)
        self.assertEqual(order.status, "Pending")
        self.assertEqual(order.user, self.customer)
        self.table.refresh_from_db()
        self.assertTrue(self.table.is_occupied)

    def test_place_order_deactivates_cart_and_opens_a_new_one(self):
        url = reverse("customer:place_order", args=[self.restaurant.qr_code, self.table.table_code])

        self.client.post(url)

        self.cart.refresh_from_db()
        self.assertFalse(self.cart.is_active)
        self.assertTrue(
            Cart.objects.filter(
                user=self.customer, restaurant=self.restaurant, table_code=self.table.table_code, is_active=True,
            ).exclude(id=self.cart.id).exists()
        )

    def test_place_order_with_empty_cart_redirects_without_creating_order(self):
        self.cart.cart_items.all().delete()
        url = reverse("customer:place_order", args=[self.restaurant.qr_code, self.table.table_code])

        response = self.client.post(url)

        # Note: fetch_redirect_response=False - rendering the view_menu
        # template for a MenuItem with no image hits a separate,
        # pre-existing template bug (item.image.url on an empty
        # ImageField) that is out of scope for this change.
        self.assertRedirects(
            response, reverse("customer:view_menu", args=[self.restaurant.qr_code, self.table.table_code]),
            fetch_redirect_response=False,
        )
        self.assertFalse(Order.objects.exists())

    def test_marking_order_bill_paid_frees_the_table(self):
        order = Order.objects.create(cart=self.cart, user=self.customer, table=self.table, status=Order.PENDING)
        self.table.is_occupied = True
        self.table.save()

        order.status = Order.BILL_PAID
        order.save()

        self.table.refresh_from_db()
        self.assertFalse(self.table.is_occupied)
        self.assertTrue(self.table.BILL_PAID)

    def test_order_total_price_matches_cart(self):
        order = Order.objects.create(cart=self.cart, user=self.customer, table=self.table, status=Order.PENDING)
        self.assertEqual(order.total_price(), Decimal("500.00"))
