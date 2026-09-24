import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Customer, Restaurant
from restaurant.models import MenuItem, Table

MENU = [
    ("Paneer Tikka", "249.00"),
    ("Masala Dosa", "149.00"),
    ("Veg Biryani", "229.00"),
    ("Tomato Soup", "119.00"),
    ("Gulab Jamun", "99.00"),
    ("Masala Chai", "49.00"),
]


class Command(BaseCommand):
    help = "Create an idempotent demo restaurant, tables, menu and customer."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD")
        if not password:
            self.stdout.write(self.style.WARNING("DEMO_PASSWORD not set; skipping seed."))
            return
        User = get_user_model()

        owner, created = User.objects.get_or_create(
            username="demo_owner",
            defaults={"email": "owner@serveware.local", "user_type": "restaurant"},
        )
        if created:
            owner.set_password(password)
            owner.save()

        restaurant, _ = Restaurant.objects.get_or_create(
            restaurant_admin=owner,
            defaults={
                "restaurant_name": "ServeWare Demo Kitchen",
                "restaurant_address": "GIFT City, Gandhinagar",
                "restaurant_pincode": "382355",
                "phone": "9876543210",
                "email": "demo@serveware.local",
            },
        )

        for n in range(1, 6):
            Table.objects.get_or_create(restaurant=restaurant, table_number=str(n), defaults={"seats": 4})

        categories = [c[0] for c in MenuItem._meta.get_field("category").choices]
        for i, (name, price) in enumerate(MENU):
            MenuItem.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={
                    "price": Decimal(price),
                    "category": categories[i % len(categories)],
                    "is_available": True,
                },
            )

        cust, created = User.objects.get_or_create(
            username="demo_customer",
            defaults={"email": "customer@serveware.local", "user_type": "customer"},
        )
        if created:
            cust.set_password(password)
            cust.save()

        Customer.objects.get_or_create(user=cust, defaults={"phone": "9123456780"})
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
