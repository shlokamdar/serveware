import base64
from io import BytesIO
import json
import logging

from django.contrib import messages
from django.db.models import Case, IntegerField, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
import qrcode

from accounts.decorators import restaurant_required
from accounts.models import Restaurant
from customer.models import Order
from restaurant.forms import MenuItemForm, RestaurantProfileForm, TableEditForm, TableForm
from restaurant.models import MenuItem, Table

logger = logging.getLogger("serveware")


def _own_restaurant(request, restaurant_code):
    return get_object_or_404(Restaurant, qr_code=restaurant_code, restaurant_admin=request.user)


@restaurant_required
def restaurant_dashboard(request):
    restaurant = get_object_or_404(Restaurant, restaurant_admin=request.user)
    return render(request, "restaurant/restaurant_dashboard.html", {"restaurant": restaurant})


@restaurant_required
def restaurant_profile_view(request):
    restaurant = get_object_or_404(Restaurant, restaurant_admin=request.user)
    qr_url = request.build_absolute_uri(reverse("restaurant:view_menu", args=[restaurant.qr_code]))
    img = qrcode.make(qr_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_data_uri = f"data:image/png;base64,{qr_b64}"
    return render(
        request,
        "restaurant/profile_view.html",
        {"restaurant": restaurant, "qr_data_uri": qr_data_uri},
    )


@restaurant_required
def restaurant_profile_edit(request):
    restaurant = get_object_or_404(Restaurant, restaurant_admin=request.user)
    if request.method == "POST":
        form = RestaurantProfileForm(request.POST, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("restaurant:restaurant_profile_view")
    else:
        form = RestaurantProfileForm(instance=restaurant)
    return render(request, "restaurant/profile_edit.html", {"form": form})


@restaurant_required
def add_tables(request):
    restaurant = request.user.restaurant
    if request.method == "POST":
        table_form = TableForm(request.POST)
        if table_form.is_valid():
            table_number = table_form.cleaned_data["table_number"]
            if Table.objects.filter(restaurant=restaurant, table_number=table_number).exists():
                table_form.add_error("table_number", "A table with this number already exists.")
            else:
                try:
                    table = table_form.save(commit=False)
                    table.restaurant = restaurant
                    table.save()
                    messages.success(request, f"Table '{table.table_number}' added successfully! QR code generated.")
                    return redirect("restaurant:view_tables")
                except Exception as e:
                    logger.exception("Error adding table")
                    messages.error(request, f"An error occurred while adding the table: {e}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        table_form = TableForm()

    return render(request, "restaurant/add_tables.html", {"table_form": table_form})


@restaurant_required
def view_tables(request):
    restaurant = request.user.restaurant
    tables = restaurant.tables.all()
    available_count = tables.filter(is_occupied=False).count()
    occupied_count = tables.filter(is_occupied=True).count()

    context = {
        "tables": tables,
        "available_count": available_count,
        "occupied_count": occupied_count,
    }
    return render(request, "restaurant/view_tables.html", context)


@restaurant_required
def view_menu(request, restaurant_code):
    restaurant = _own_restaurant(request, restaurant_code)
    menu_items = MenuItem.objects.filter(restaurant=restaurant)
    categories = {
        "Appetizers": menu_items.filter(category="Appetizers"),
        "Main Course": menu_items.filter(category="Main Course"),
        "Desserts": menu_items.filter(category="Desserts"),
        "Beverages": menu_items.filter(category="Beverages"),
        "Vegan": menu_items.filter(category="Vegan"),
        "Non-Veg": menu_items.filter(category="Non-Veg"),
        "Pure Veg": menu_items.filter(category="Pure Veg"),
        "Chef's Special": menu_items.filter(category="Chef's Special"),
        "Soups": menu_items.filter(category="Soups"),
        "Jain": menu_items.filter(category="Jain"),
    }
    context = {
        "restaurant": restaurant,
        "categories": categories,
    }
    return render(request, "restaurant/menu.html", context)


@restaurant_required
def add_menu_item(request, restaurant_code):
    restaurant = _own_restaurant(request, restaurant_code)
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.restaurant = restaurant
            menu_item.is_available = True
            menu_item.save()
            return redirect("restaurant:view_menu", restaurant_code=restaurant.qr_code)
    else:
        form = MenuItemForm()
    return render(request, "restaurant/add_item.html", {"form": form, "restaurant": restaurant})


@restaurant_required
def edit_menu_item(request, restaurant_code, item_id):
    restaurant = _own_restaurant(request, restaurant_code)
    item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect("restaurant:view_menu", restaurant_code=restaurant.qr_code)
    else:
        form = MenuItemForm(instance=item)
    return render(request, "restaurant/edit_item.html", {"form": form, "item": item, "restaurant": restaurant})


@restaurant_required
@require_POST
def delete_menu_item(request, restaurant_code, item_id):
    restaurant = _own_restaurant(request, restaurant_code)
    get_object_or_404(MenuItem, id=item_id, restaurant=restaurant).delete()
    return redirect("restaurant:view_menu", restaurant_code=restaurant_code)


@restaurant_required
def view_orders(request):
    restaurant = request.user.restaurant
    orders = Order.objects.filter(table__restaurant=restaurant)
    status_choices = Order.STATUS_CHOICES
    orders = orders.annotate(
        custom_order=Case(
            When(status="Bill_Paid", then=2),
            When(status="Completed", then=1),
            default=0,
            output_field=IntegerField(),
        )
    ).order_by("custom_order", "order_date")

    pending_count = orders.filter(status="Pending").count()
    active_count = orders.filter(status__in=["Cooking", "Ready_to_serve"]).count()
    completed_count = orders.filter(status="Completed").count()

    context = {
        "orders": orders,
        "pending_count": pending_count,
        "active_count": active_count,
        "completed_count": completed_count,
        "status_choices": status_choices,
    }
    return render(request, "restaurant/view_orders.html", context)


@restaurant_required
@require_POST
def update_order_status(request, order_id):
    restaurant = request.user.restaurant
    order = get_object_or_404(Order, id=order_id, table__restaurant=restaurant)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    new_status = data.get("status")
    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({"error": "invalid status"}, status=400)

    order.status = new_status
    order.save()
    if order.table:
        order.table.update_table_status()

    return JsonResponse({"success": True})


@restaurant_required
def order_details(request, order_id):
    try:
        restaurant = request.user.restaurant
        order = Order.objects.select_related("cart", "table").get(id=order_id, table__restaurant=restaurant)
        items = order.cart.cart_items.all() if order.cart else []
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect("restaurant:view_orders")

    context = {"order": order, "items": items}
    return render(request, "restaurant/order_details.html", context)


@restaurant_required
def edit_table(request, table_id):
    table = get_object_or_404(Table, id=table_id, restaurant__restaurant_admin=request.user)
    if request.method == "POST":
        form = TableEditForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            return redirect("restaurant:view_tables")
    else:
        form = TableEditForm(instance=table)

    return render(request, "restaurant/edit_table.html", {"form": form, "table": table})
