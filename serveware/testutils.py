import itertools
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import Customer, Restaurant
from restaurant.models import MenuItem, Table

PASSWORD = "Str0ng-Test-Pass!"
_counter = itertools.count(1)
_MEDIA = tempfile.mkdtemp(prefix="serveware-test-media-")
User = get_user_model()


@override_settings(MEDIA_ROOT=_MEDIA, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ServeWareTestCase(TestCase):
    """Base class: isolated media dir + in-memory email for every test."""


def make_restaurant_owner():
    n = next(_counter)
    user = User.objects.create_user(
        username=f"owner{n}",
        email=f"owner{n}@test.local",
        password=PASSWORD,
        user_type="restaurant",
    )
    restaurant = Restaurant.objects.create(
        restaurant_admin=user,
        restaurant_name=f"Test Resto {n}",
        restaurant_address="1 Test Street",
        restaurant_pincode="380001",
        phone="9876543210",
        email=f"resto{n}@test.local",
    )
    return user, restaurant


def make_customer():
    n = next(_counter)
    user = User.objects.create_user(
        username=f"cust{n}",
        email=f"cust{n}@test.local",
        password=PASSWORD,
        user_type="customer",
    )
    Customer.objects.create(user=user, phone="9123456780")
    return user


def make_table(restaurant, number="1", seats=4):
    return Table.objects.create(restaurant=restaurant, table_number=number, seats=seats)


def make_menu_item(restaurant, name="Paneer Tikka", price="249.00"):
    category = MenuItem._meta.get_field("category").choices[0][0]
    return MenuItem.objects.create(
        restaurant=restaurant,
        name=name,
        price=Decimal(price),
        category=category,
        is_available=True,
    )
