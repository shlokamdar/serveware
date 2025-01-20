from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Restaurant
from restaurant.models import Table, MenuItem
from restaurant.forms import RestaurantProfileForm, TableForm, MenuItemForm, TableEditForm
import qrcode
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
from customer.models import Order
from django.db.models import Case, When, IntegerField
from django.views.decorators.csrf import csrf_protect
import json

def is_restaurant_admin(user):
    return user.is_authenticated and hasattr(user, 'restaurant')

def restaurant_dashboard(request):
    if request.user.is_authenticated:
        restaurant = get_object_or_404(Restaurant, restaurant_admin=request.user)
        return render(request, 'restaurant/restaurant_dashboard.html', {'restaurant': restaurant})
    else:
        return redirect('login')

@login_required
def restaurant_profile_view(request):
    restaurant = get_object_or_404(Restaurant, restaurant_admin=request.user)
    return render(request, 'restaurant/profile_view.html', {'restaurant': restaurant})

@login_required
def restaurant_profile_edit(request):
    restaurant = get_object_or_404(Restaurant, restaurant_admin=request.user)
    if request.method == 'POST':
        form = RestaurantProfileForm(request.POST, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('restaurant:restaurant_profile_view')
    else:
        form = RestaurantProfileForm(instance=restaurant)
    return render(request, 'restaurant/profile_edit.html', {'form': form})

@login_required
def add_tables(request):
    if request.method == 'POST':
        table_form = TableForm(request.POST)
        if table_form.is_valid():
            table_number = table_form.cleaned_data['table_number']
            restaurant = request.user.restaurant
            if Table.objects.filter(restaurant=restaurant, table_number=table_number).exists():
                table_form.add_error('table_number', 'A table with this number already exists.')
            else:
                try:
                    table = table_form.save(commit=False)
                    table.restaurant = restaurant
                    table.save()
                    messages.success(request, f"Table '{table.table_number}' added successfully! QR code generated.")
                    return redirect('restaurant:view_tables')
                except Exception as e:
                    messages.error(request, f"An error occurred while adding the table: {e}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        table_form = TableForm()
    
    return render(request, 'restaurant/add_tables.html', {'table_form': table_form})

def view_tables(request):
    restaurant = request.user.restaurant
    tables = restaurant.tables.all()
    qr_codes = []
    for table in tables:
        qr_data = f"restaurant/{restaurant.id}/table/{table.id}"
        img = qrcode.make(qr_data)
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        fs = FileSystemStorage(location='static/qr_codes/')
        file_name = f"qr_table_{table.table_number}.png"
        fs.save(file_name, buffer)
        qr_codes.append({
            'table': table,
            'qr_code_url': fs.url(file_name)
        })

    available_count = tables.filter(is_occupied=False).count()
    occupied_count = tables.filter(is_occupied=True).count()
    
    context = {
        'tables': tables,
        'available_count': available_count,
        'occupied_count': occupied_count,
        'qr_codes': qr_codes
    }
    
    return render(request, 'restaurant/view_tables.html', context)

def get_table_status(request):
    tables = Table.objects.all()
    table_data = [{'id': table.id, 'is_occupied': table.is_occupied, 'table_number': table.table_number} for table in tables]
    return JsonResponse({'tables': table_data})

def view_menu(request, restaurant_code):
    restaurant = get_object_or_404(Restaurant, qr_code=restaurant_code)
    menu_items = MenuItem.objects.filter(restaurant=restaurant)
    categories = {
        'Appetizers': menu_items.filter(category='Appetizers'),
        'Main Course': menu_items.filter(category='Main Course'),
        'Desserts': menu_items.filter(category='Desserts'),
        'Beverages': menu_items.filter(category='Beverages'),
        'Vegan': menu_items.filter(category='Vegan'),
        'Non-Veg': menu_items.filter(category='Non-Veg'),
        'Pure Veg': menu_items.filter(category='Pure Veg'),
        "Chef's Special": menu_items.filter(category="Chef's Special"),
        'Soups': menu_items.filter(category='Soups'),
        'Jain': menu_items.filter(category='Jain'),
    }
    context = {
        'restaurant': restaurant,
        'categories': categories,
    }
    return render(request, 'restaurant/menu.html', context)

def add_menu_item(request, restaurant_code):
    restaurant = get_object_or_404(Restaurant, qr_code=restaurant_code)
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.restaurant = restaurant
            menu_item.is_available = True
            menu_item.save()
            return redirect('restaurant:view_menu', restaurant_code=restaurant.qr_code)
    else:
        form = MenuItemForm()
    return render(request, 'restaurant/add_item.html', {'form': form, 'restaurant': restaurant})

def edit_menu_item(request, restaurant_code, item_id):
    restaurant = get_object_or_404(Restaurant, qr_code=restaurant_code)
    item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('restaurant:view_menu', restaurant_code=restaurant.qr_code)
    else:
        form = MenuItemForm(instance=item)
    return render(request, 'restaurant/edit_item.html', {'form': form, 'item': item, 'restaurant': restaurant})

def delete_menu_item(request, restaurant_code, item_id):
    item = get_object_or_404(MenuItem, id=item_id, restaurant__qr_code=restaurant_code)
    restaurant_code = item.restaurant.qr_code
    item.delete()
    return redirect('restaurant:view_menu', restaurant_code=restaurant_code)

@login_required
def view_orders(request):
    restaurant = request.user.restaurant
    orders = Order.objects.filter(table__restaurant=restaurant)
    status_choices = Order.STATUS_CHOICES
    orders = orders.annotate(
        custom_order=Case(
            When(status='Bill Paid', then=2),  
            When(status='Completed', then=1),  
            default=0, 
            output_field=IntegerField(),
        )
    ).order_by('custom_order', 'order_date')

    pending_count = orders.filter(status='Pending').count()
    active_count = orders.filter(status__in=['Cooking', 'Ready_to_serve']).count()
    completed_count = orders.filter(status='Completed').count()

    context = {
        'orders': orders,
        'pending_count': pending_count,
        'active_count': active_count,
        'completed_count': completed_count,
        'status_choices': status_choices,
    }

    return render(request, 'restaurant/view_orders.html', context)

@csrf_protect
@login_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        try:
            restaurant = request.user.restaurant
            order = Order.objects.get(id=order_id, table__restaurant=restaurant)
            data = json.loads(request.body)
            new_status = data.get('status')
            valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
            order.status = new_status
            order.save()
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def order_details(request, order_id):
    try:
        restaurant = request.user.restaurant
        order = Order.objects.select_related('cart', 'table').get(id=order_id, table__restaurant=restaurant)
        items = order.cart.cart_items.all()  
    except Order.DoesNotExist:
        return redirect('restaurant:manage_orders')  

    context = {'order': order, 'items': items}
    return render(request, 'restaurant/order_details.html', context)


def edit_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)  
    if request.method == 'POST':
        form = TableEditForm(request.POST, instance=table)
        if form.is_valid():
            form.save()  
            return redirect('restaurant:view_tables') 
    else:
        form = TableEditForm(instance=table)
    
    return render(request, 'restaurant/edit_table.html', {'form': form, 'table': table})