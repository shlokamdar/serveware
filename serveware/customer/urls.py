from django.urls import path
from customer import views
app_name  = 'customer'

urlpatterns = [
    # Dashboard URLs
    path('customer-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('scan-qr/', views.scan_qr, name='scan_qr'),

    path('menu/<str:qr_code>/<str:table_code>/', views.view_menu, name='view_menu'),
    path('menu/<str:qr_code>/<str:table_code>/item/<int:item_id>/', views.view_item_details, name='view_item_details'),

    path('<str:qr_code>/<str:table_code>/add_to_cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('customer/<str:qr_code>/<str:table_code>/cart/', views.view_cart, name='view_cart'),

    path('cart/update/<int:item_id>/<str:action>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('delete_cart_item/<int:item_id>/', views.delete_cart_item, name='delete_cart_item'),

    path('place_order/<str:qr_code>/<str:table_code>/', views.place_order, name='place_order'),
    path('view-orders/<str:qr_code>/<str:table_code>/', views.view_orders, name='view_orders'),
]
