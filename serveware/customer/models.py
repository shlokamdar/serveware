from django.conf import settings
from django.db import models
from restaurant.models import MenuItem, Restaurant, Table


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True)
    table_code = models.CharField(max_length=10, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Cart for {self.user}"

    def total_price(self):
        return sum(item.total_price() for item in self.cart_items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items', null=True)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"

    def total_price(self):
        return self.menu_item.price * self.quantity

    class Meta:
        unique_together = ('cart', 'menu_item')


class Order(models.Model):
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, null=True, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)

    PENDING = 'Pending'
    COOKING = 'Cooking'
    READY_TO_SERVE = 'Ready_to_serve'
    COMPLETED = 'Completed'
    CANCELED = 'Canceled'
    BILL_PAID = 'Bill_Paid'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COOKING, 'Cooking'),
        (READY_TO_SERVE, 'Ready_to_serve'),
        (COMPLETED, 'Completed'),
        (CANCELED, 'Canceled'),
        (BILL_PAID, 'Bill_Paid'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=PENDING)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            try:
                old_status = Order.objects.get(pk=self.pk).status
            except Order.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if self.table and (is_new or old_status != self.status or self.status == self.BILL_PAID):
            self.table.update_table_status()

    def __str__(self):
        who = self.user.username if self.user else "guest"
        return f"Order #{self.pk} ({self.status}) by {who}"

    def total_price(self):
        return self.cart.total_price() if self.cart else 0
