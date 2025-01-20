from django.contrib import admin
from .models import Cart, CartItem, Order

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class CartAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'restaurant', 'table_code', 'created_at', 'total_price','is_active')
    list_filter = ('restaurant', 'created_at')
    readonly_fields = ('total_price',)

    def total_price(self, obj):
        return obj.total_price()
    total_price.short_description = "Total Price"

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'menu_item', 'quantity', 'total_price')
    list_filter = ('menu_item__restaurant',)

    def total_price(self, obj):
        return obj.total_price()
    total_price.short_description = "Total Price"

admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'order_date','table')
admin.site.register(Order, OrderAdmin)
