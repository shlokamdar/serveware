import logging
from urllib.parse import urlparse

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import customer_required
from accounts.models import Restaurant
from customer.models import Cart, CartItem, Order
from restaurant.models import MenuItem, Table

logger = logging.getLogger("serveware")


def _parse_qr_payload(raw):
    """Accept either a full URL (http://.../customer/menu/<qr>/<table>/) or path."""
    if not raw:
        return None, None
    raw_str = raw.strip()
    parts = [p for p in urlparse(raw_str).path.split("/") if p]
    if "menu" in parts:
        i = parts.index("menu")
        if len(parts) >= i + 3:
            return parts[i + 1], parts[i + 2]
    # Fallback if raw was entered as "restaurant_code/table_code"
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


@customer_required
def customer_dashboard(request):
    return render(request, "customer/customer_dashboard.html")


@customer_required
def scan_qr(request):
    if request.method == "POST":
        raw = request.POST.get("restaurant_code", "")
        restaurant_code, table_code = _parse_qr_payload(raw)
        if not restaurant_code or not table_code:
            messages.error(request, "Invalid QR code format. Please scan or enter a valid QR URL.")
            return render(request, "customer/scan_qr.html")

        restaurant = Restaurant.objects.filter(qr_code=restaurant_code).first()
        if not restaurant:
            messages.error(request, "Restaurant not found.")
            return render(request, "customer/scan_qr.html")

        table = Table.objects.filter(restaurant=restaurant, table_code=table_code).first()
        if not table:
            messages.error(request, "Table not found for this restaurant.")
            return render(request, "customer/scan_qr.html")

        request.session["qr_code"] = restaurant.qr_code
        request.session["table_number"] = table.table_code
        return redirect("customer:view_menu", qr_code=restaurant.qr_code, table_code=table.table_code)

    return render(request, "customer/scan_qr.html")


@customer_required
def view_menu(request, qr_code, table_code):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    get_object_or_404(Table, restaurant=restaurant, table_code=table_code)

    menu_items = restaurant.menu_items.all()
    categories = {}
    for item in menu_items:
        categories.setdefault(item.category, []).append(item)

    return render(
        request,
        "customer/customer_menu.html",
        {
            "restaurant": restaurant,
            "categories": categories,
            "table_code": table_code,
            "qr_code": qr_code,
        },
    )


@customer_required
def view_item_details(request, qr_code, table_code, item_id):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    more_options = MenuItem.objects.filter(category=menu_item.category, restaurant=restaurant).exclude(id=item_id)

    context = {
        "menu_item": menu_item,
        "restaurant": restaurant,
        "more_options": more_options,
        "table_code": table_code,
        "qr_code": qr_code,
    }
    return render(request, "customer/view_item_details.html", context)


@customer_required
@require_POST
def add_to_cart(request, qr_code, table_code, item_id):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)

    cart, _ = Cart.objects.get_or_create(
        user=request.user,
        restaurant=restaurant,
        table_code=table_code,
        is_active=True,
    )
    cart_item, created = CartItem.objects.get_or_create(cart=cart, menu_item=menu_item)
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    logger.info("Added item %s to cart %s (quantity=%s)", menu_item.name, cart.id, cart_item.quantity)
    messages.success(request, f"{menu_item.name} has been added to your cart!")
    return redirect("customer:view_menu", qr_code=qr_code, table_code=table_code)


@customer_required
def view_cart(request, qr_code, table_code):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    cart = Cart.objects.filter(
        user=request.user,
        restaurant=restaurant,
        table_code=table_code,
        is_active=True,
    ).first()

    if not cart:
        cart = Cart.objects.create(
            user=request.user,
            restaurant=restaurant,
            table_code=table_code,
            is_active=True,
        )

    cart_items = cart.cart_items.all()
    total_price = cart.total_price()

    return render(
        request,
        "customer/view_cart.html",
        {
            "cart_items": cart_items,
            "total_price": total_price,
            "table_code": table_code,
            "qr_code": qr_code,
        },
    )


@customer_required
def update_cart_quantity(request, item_id, action):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if action == "increment":
        cart_item.quantity += 1
    elif action == "decrement" and cart_item.quantity > 1:
        cart_item.quantity -= 1
    else:
        messages.error(request, "Invalid action or minimum quantity reached.")
        return redirect(
            "customer:view_cart",
            qr_code=cart_item.cart.restaurant.qr_code,
            table_code=cart_item.cart.table_code,
        )

    _line_total = cart_item.quantity * cart_item.menu_item.price  # local variable, not instance field
    cart_item.save()
    messages.success(request, "Cart updated successfully.")
    return redirect(
        "customer:view_cart",
        qr_code=cart_item.cart.restaurant.qr_code,
        table_code=cart_item.cart.table_code,
    )


@customer_required
@require_POST
def delete_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    restaurant_qr = cart_item.cart.restaurant.qr_code if cart_item.cart and cart_item.cart.restaurant else None
    table_code = cart_item.cart.table_code if cart_item.cart else None
    cart_item.delete()
    messages.success(request, "Item removed from the cart successfully.")
    if restaurant_qr and table_code:
        return redirect("customer:view_cart", qr_code=restaurant_qr, table_code=table_code)
    return redirect("customer:customer_dashboard")


@customer_required
def place_order(request, qr_code, table_code):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    table = get_object_or_404(Table, restaurant=restaurant, table_code=table_code)

    cart = Cart.objects.filter(
        user=request.user,
        restaurant=restaurant,
        table_code=table_code,
        is_active=True,
    ).first()

    if not cart or not cart.cart_items.exists():
        messages.error(request, "Your cart is empty. Add items to proceed.")
        return redirect("customer:view_menu", qr_code=qr_code, table_code=table_code)

    if request.method == "POST":
        order = Order.objects.create(
            cart=cart,
            user=request.user,
            table=table,
            status="Pending",
        )
        table.is_occupied = True
        table.save(update_fields=["is_occupied"])
        table.update_table_status()

        cart.is_active = False
        cart.save(update_fields=["is_active"])

        # Create fresh active cart for next order
        Cart.objects.create(
            user=request.user,
            restaurant=restaurant,
            table_code=table_code,
            is_active=True,
        )

        return render(
            request,
            "customer/order_confirmation.html",
            {
                "order": order,
                "cart": cart,
                "restaurant": restaurant,
                "table": table,
                "qr_code": qr_code,
                "table_code": table_code,
            },
        )

    return render(
        request,
        "customer/order_confirmation.html",
        {
            "cart": cart,
            "restaurant": restaurant,
            "table": table,
            "qr_code": qr_code,
            "table_code": table_code,
        },
    )


@customer_required
def view_orders(request, qr_code, table_code):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    table = get_object_or_404(Table, restaurant=restaurant, table_code=table_code)
    orders = Order.objects.filter(user=request.user, table=table)
    message = "No orders found for this table." if not orders else None

    return render(
        request,
        "customer/view_orders.html",
        {
            "orders": orders,
            "table_code": table_code,
            "qr_code": qr_code,
            "message": message,
        },
    )
