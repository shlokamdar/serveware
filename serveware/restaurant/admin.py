# admin.py of your restaurant app
from django.contrib import admin
from .models import Table, MenuItem

# Register Table model
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'restaurant', 'seats', 'is_occupied', 'table_code', 'qr_code_image','BILL_PAID')
    search_fields = ('table_number', 'restaurant__name', 'table_code')
    list_filter = ('is_occupied', 'restaurant')
admin.site.register(Table, TableAdmin)



@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'restaurant', 'is_spicy', 'is_popular', 'is_vegan', 'is_non_veg', 'is_jain_option', 'is_chefs_special', 'is_soup','is_available')
    search_fields = ('name', 'restaurant__name', 'category')
    list_filter = ('category', 'is_spicy', 'is_popular', 'is_vegan', 'is_non_veg', 'is_jain_option', 'is_chefs_special', 'is_soup')

