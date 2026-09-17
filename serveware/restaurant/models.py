# models/resturant app
import logging
import uuid
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import models

from accounts.models import Restaurant

logger = logging.getLogger(__name__)


# Helper function to generate unique codes
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

    def update_table_status(self):
        # Local import to avoid a circular import: customer.models imports
        # Table from this module, so this module cannot import
        # customer.models at load time.
        from customer.models import Order

        logger.debug("Updating status for table %s", self.table_number)
        orders = self.orders.all()  # Fetch all associated orders
        logger.debug("Number of orders associated with the table: %d", orders.count())

        if orders.exists():
            if any(order.status == Order.BILL_PAID for order in orders):
                logger.debug("At least one order is Bill Paid for table %s. Marking table as free.", self.table_number)
                self.BILL_PAID = True
                self.is_occupied = False
            else:
                self.is_occupied = True
                self.BILL_PAID = False
                logger.debug("No orders are Bill Paid for table %s. Keeping table occupied.", self.table_number)
        else:
            self.is_occupied = False
            self.BILL_PAID = False
            logger.debug("No orders on table %s. Marking as free.", self.table_number)

        self.save()
        logger.debug(
            "Final table status for %s - Occupied: %s, Bill Paid: %s",
            self.table_number, self.is_occupied, self.BILL_PAID,
        )

    def __str__(self):
        return f"Table {self.table_number} ({self.seats} seats)"

    def save(self, *args, **kwargs):
        if not self.qr_code_image:
            qr_data = f"/customer/{self.restaurant.qr_code}/{self.table_code}/menu"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            file_name = f"table_{self.restaurant.qr_code}_{self.table_code}.png"
            self.qr_code_image.save(file_name, ContentFile(buffer.getvalue()), save=False)
        
        super().save(*args, **kwargs)

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
    is_available = models.BooleanField(default=True)  # New field to track availability

    def __str__(self):
        return self.name
