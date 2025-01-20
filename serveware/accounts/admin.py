from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Restaurant, Customer


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_active')


class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('restaurant_name', 'restaurant_admin', 'restaurant_address', 'phone', 'email', 'qr_code')


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone','dob','is_birthday')
    

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Customer, CustomerAdmin)
