#models/accounts app 
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
import uuid
from datetime import date

# Helper function to generate unique codes
def generate_unique_code():
    return str(uuid.uuid4())[:8]

# Custom User model
class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('restaurant', 'Restaurant'),
        ('customer', 'Customer'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)

# Restaurant model
class Restaurant(models.Model):
    restaurant_admin = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restaurant')
    restaurant_name = models.CharField(max_length=255)
    restaurant_address = models.TextField()
    restaurant_landmark = models.CharField(max_length=255, null=True, blank=True)
    restaurant_pincode = models.CharField(
        max_length=6,
        validators=[RegexValidator(regex=r'^\d{6}$', message='Pincode must be exactly 6 digits')]
    )
    phone = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^\d{10}$', message='Phone number must be of 10 digits')]
    )
    email = models.EmailField(unique=True)
    gst_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    qr_code = models.CharField(max_length=10, unique=True, default=generate_unique_code) ### 

    def __str__(self):
        return self.restaurant_name
    
# Customer model
class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^\d{10}$', message='Phone number must be of 10 digits')]
    )
    dob = models.DateField(null=True, blank=True) 
    date_joined = models.DateField(auto_now_add=True) 
    
    @property
    def is_birthday(self):
        if self.dob:
            today = date.today()
            return self.dob.day == today.day and self.dob.month == today.month
        return False

    def __str__(self):
        return self.user.username
