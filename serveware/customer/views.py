import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Restaurant
from restaurant.models import MenuItem, Table
from .models import Cart, CartItem, Order

logger = logging.getLogger(__name__)

@login_required
def customer_dashboard(request):
    return render(request, 'customer/customer_dashboard.html')


@login_required
def scan_qr(request):
    if request.method == 'POST':
        restaurant_code = request.POST.get('restaurant_code')
        try:
            logger.debug("Received QR code: %s", restaurant_code)
            parts = restaurant_code.strip('/').split('/')
            if len(parts) >= 3:
                restaurant_code = parts[1]
                table_code = parts[2]
                logger.debug("Extracted restaurant code: %s, table code: %s", restaurant_code, table_code)

                restaurant = Restaurant.objects.get(qr_code=restaurant_code)
                logger.debug("Found restaurant: %s", restaurant)

                table = Table.objects.get(restaurant=restaurant, table_code=table_code)
                logger.debug("Found table: %s", table)

                request.session['qr_code'] = restaurant_code
                request.session['table_number'] = table_code

                return redirect('customer:view_menu', qr_code=restaurant.qr_code, table_code=table.table_code)
            else:
                raise ValueError("Invalid QR code format.")
        except (Restaurant.DoesNotExist, Table.DoesNotExist, ValueError) as e:
            logger.warning("Invalid QR code scan: %s", e)
            error = f"Invalid QR code or table information: {e}"
            return render(request, 'customer/scan_qr.html', {'error': error})
    return render(request, 'customer/scan_qr.html')


@login_required
def view_menu(request, qr_code, table_code):
    logger.debug("View menu - QR code: %s, table code: %s", qr_code, table_code)
    try:
        restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
        logger.debug("Restaurant found: %s", restaurant)

        table = get_object_or_404(Table, restaurant=restaurant, table_code=table_code)
        logger.debug("Table found: %s", table)

        menu_items = restaurant.menu_items.all()
        categories = {}
        for item in menu_items:
            category_name = item.category
            if category_name not in categories:
                categories[category_name] = []
            categories[category_name].append(item)

        return render(request, 'customer/customer_menu.html', {
            'restaurant': restaurant,
            'categories': categories,
            'table_code': table_code,
            'qr_code': qr_code,

        })
    except Exception as e:
        logger.exception("Error rendering menu for qr_code=%s, table_code=%s", qr_code, table_code)
        return render(request, 'customer/customer_menu.html', {'error': f"Error: {e}"})


@login_required
def view_item_details(request, qr_code, table_code, item_id):
    try:
        restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
        menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)

        more_options = MenuItem.objects.filter(category=menu_item.category, restaurant=restaurant).exclude(id=item_id)

        context = {
            'menu_item': menu_item,
            'restaurant': restaurant,
            'more_options': more_options,
            'table_code': table_code,
            'qr_code': qr_code,
        }

        return render(request, 'customer/view_item_details.html', context)

    except Restaurant.DoesNotExist:
        return render(request, 'customer/404.html', {'error': "Restaurant not found"})



def add_to_cart(request, qr_code, table_code, item_id):
    try:
        if not request.user.is_authenticated:
            messages.error(request, "You need to log in to add items to the cart.")
            return redirect('accounts:login')

        restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
        menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)

        cart = Cart.objects.filter(
            user=request.user,
            restaurant=restaurant,
            table_code=table_code,
            is_active=True
        ).first()

        if not cart:
            cart = Cart.objects.create(
                user=request.user,
                restaurant=restaurant,
                table_code=table_code,
                is_active=True
            )

        logger.debug("Cart details - id: %s, active: %s, user: %s", cart.id, cart.is_active, cart.user.username)

        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, menu_item=menu_item)

        if not item_created:
            cart_item.quantity += 1
            cart_item.save()

        logger.debug("Cart item added - menu item: %s, quantity: %s", menu_item.name, cart_item.quantity)

        messages.success(request, f"{menu_item.name} has been added to your cart!")
        return redirect('customer:view_menu', qr_code=qr_code, table_code=table_code)

    except Exception:
        messages.error(request, "Something went wrong while adding the item to your cart.")
        logger.exception("Error adding item %s to cart for qr_code=%s, table_code=%s", item_id, qr_code, table_code)
        return redirect('customer:view_menu', qr_code=qr_code, table_code=table_code)


@login_required
def view_cart(request, qr_code, table_code):
    logger.debug("View cart - QR code: %s, table code: %s", qr_code, table_code)
    try:
        restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
        logger.debug("Restaurant found: %s", restaurant.restaurant_name)

        cart = Cart.objects.filter(
            user=request.user,
            restaurant=restaurant,
            table_code=table_code,
            is_active=True
        ).first()

        if not cart:
            cart = Cart.objects.create(
                user=request.user,
                restaurant=restaurant,
                table_code=table_code,
                is_active=True
            )
            logger.debug("New active cart created with id: %s", cart.id)

        if cart:
            logger.debug("Cart found: id=%s, active=%s", cart.id, cart.is_active)

            if not cart.is_active:
                logger.debug("Cart is inactive; changing cart's is_active status to True.")
                cart.is_active = True
                cart.save()

            for cart_item in cart.cart_items.all():
                logger.debug(
                    "Cart item - id: %s, menu item: %s, quantity: %s",
                    cart_item.id, cart_item.menu_item.name, cart_item.quantity,
                )
        else:
            logger.debug("No cart found for the given parameters.")

        if not cart or not cart.is_active:
            messages.error(request, "This cart is no longer active. Please start a new order.")
            logger.debug("Cart is inactive or doesn't exist.")
            return redirect('customer:view_menu', qr_code=qr_code, table_code=table_code)

        cart_items = cart.cart_items.all()
        total_price = cart.total_price()
        logger.debug("Total price for the cart: %s", total_price)

        return render(request, 'customer/view_cart.html', {
            'cart_items': cart_items,
            'total_price': total_price,
            'table_code': table_code,
            'qr_code': qr_code,
        })

    except Exception:
        messages.error(request, "Something went wrong while viewing the cart.")
        logger.exception("Error viewing cart for qr_code=%s, table_code=%s", qr_code, table_code)
        return redirect('customer:view_menu', qr_code=qr_code, table_code=table_code)


@login_required
def update_cart_quantity(request, item_id, action):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if action == 'increment':
            cart_item.quantity += 1
        elif action == 'decrement' and cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            messages.error(request, "Invalid action or minimum quantity reached.")
            return redirect('customer:view_cart', qr_code=cart_item.cart.restaurant.qr_code, table_code=cart_item.cart.table_code)

        cart_item.total_price = cart_item.quantity * cart_item.menu_item.price
        cart_item.save()

        messages.success(request, "Cart updated successfully.")

    except Exception:
        messages.error(request, "Something went wrong while updating the cart.")
        logger.exception("Error updating quantity for cart item %s", item_id)

    return redirect('customer:view_cart', qr_code=cart_item.cart.restaurant.qr_code, table_code=cart_item.cart.table_code)

def delete_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)

    if cart_item.cart.user == request.user:
        cart_item.delete()
        messages.success(request, 'Item removed from the cart successfully.')
    else:
        messages.error(request, 'You are not authorized to delete this item.')

    return redirect('customer:view_cart', qr_code=cart_item.cart.restaurant.qr_code, table_code=cart_item.cart.table_code)




from django.shortcuts import get_object_or_404
from django.contrib import messages
from .models import Cart, Order, Table, Restaurant

@login_required
def place_order(request, qr_code, table_code):
    restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
    table = get_object_or_404(Table, restaurant=restaurant, table_code=table_code)

    try:
        cart = Cart.objects.filter(user=request.user, cart_items__isnull=False, is_active=True).latest('created_at')
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty. Add items to proceed.")
        return redirect('customer:view_menu', qr_code=qr_code, table_code=table_code)

    if request.method == 'POST':

        order = Order.objects.create(
            cart=cart,
            user=request.user,
            table=table,
            status='Pending'
        )

        table.is_occupied = True
        table.save()
        table.update_table_status()

        cart.is_active = False
        cart.save()

        Cart.objects.create(
            user=request.user,
            restaurant=restaurant,
            table_code=table_code,
            is_active=True
        )

        return render(request, 'customer/order_confirmation.html', {
            'order': order,
            'cart': cart,
            'restaurant': restaurant,
            'table': table,
            'qr_code': qr_code,
            'table_code': table_code
        })

    return render(request, 'customer/order_confirmation.html', {
        'cart': cart,
        'restaurant': restaurant,
        'table': table,
        'qr_code': qr_code,
        'table_code': table_code
    })



@login_required
def view_orders(request, qr_code, table_code):
    try:
        restaurant = get_object_or_404(Restaurant, qr_code=qr_code)
        table = get_object_or_404(Table, restaurant=restaurant, table_code=table_code)
        orders = Order.objects.filter(user=request.user, table=table)

        if not orders:
            message = "No orders found for this table."
        else:
            message = None

        return render(request, 'customer/view_orders.html', {
            'orders': orders,
            'table_code': table_code,
            'qr_code': qr_code,
            'message': message,
        })

    except Exception as e:
        logger.exception("Error viewing orders for qr_code=%s, table_code=%s", qr_code, table_code)
        return render(request, 'customer/view_orders.html', {'error': f"An error occurred: {e}"})
