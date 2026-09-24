from io import BytesIO
import uuid
import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from accounts.models import Restaurant


def generate_unique_code():
    return str(uuid.uuid4())[:8]


class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=25)
    seats = models.PositiveIntegerField()
    is_occupied = models.BooleanField(default=False)
    table_code = models.CharField(max_length=10, unique=True, default=generate_unique_code)
    qr_code_image = models.ImageField(upload_to='table_qr/', blank=True, null=True)
    BILL_PAID = models.BooleanField(default=False)

    def menu_path(self):
        """Single source of truth for the URL encoded into the table's QR code."""
        return reverse("customer:view_menu", args=[self.restaurant.qr_code, self.table_code])

    def update_table_status(self):
        active = self.orders.exclude(status__in=["Bill_Paid", "Canceled"]).exists()
        self.is_occupied = active
        self.BILL_PAID = (not active) and self.orders.filter(status="Bill_Paid").exists()
        super().save(update_fields=["is_occupied", "BILL_PAID"])

    def __str__(self):
        return f"Table {self.table_number} ({self.seats} seats)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.qr_code_image:
            data = f"{settings.SITE_URL}{self.menu_path()}"
            img = qrcode.make(data)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            self.qr_code_image.save(f"table_{self.table_code}.png", ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=["qr_code_image"])


class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('Appetizers', 'Appetizers'),
        ('Main Course', 'Main Course'),
        ('Desserts', 'Desserts'),
        ('Beverages', 'Beverages'),
        ('Soups', 'Soups'),
        ('Vegan', 'Vegan'),
        ('Non-Veg', 'Non-Veg'),
        ('Pure Veg', 'Pure Veg'),
        ('Chef\'s Special', 'Chef\'s Special'),
        ('Jain', 'Jain'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    is_spicy = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_jain_option = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_non_veg = models.BooleanField(default=False)
    is_pure_veg = models.BooleanField(default=False)
    is_chefs_special = models.BooleanField(default=False)
    is_soup = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name
