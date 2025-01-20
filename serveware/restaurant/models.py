# models/resturant app
from django.db import models
from accounts.models import Restaurant
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

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
        print(f"Debug: Updating status for table {self.table_number}")  # Debugging print statement
        orders = self.orders.all()  # Fetch all associated orders
        print(f"Debug: Number of orders associated with the table: {orders.count()}")  # Debugging print

        if orders.exists():
            
            if any(order.status == self.BILL_PAID for order in orders):
                print(f"Debug: At least one order is Bill Paid for table {self.table_number}. Marking table as free.")
                self.bill_paid = True
                self.is_occupied = False  
            else:
                self.is_occupied = True
                self.bill_paid = False
                print(f"Debug: No orders are Bill Paid for table {self.table_number}. Keeping table occupied.")
        else:
            self.is_occupied = False
            self.bill_paid = False
            print(f"Debug: No orders on table {self.table_number}. Marking as free.")

        self.save()  
        print(f"Debug: Final table status for {self.table_number} - Occupied: {self.is_occupied}, Bill Paid: {self.bill_paid}")




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
