from django.urls import path
from restaurant import views
app_name  = 'restaurant'

urlpatterns = [
    path('restaurant-dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),

    path('profile/', views.restaurant_profile_view, name='restaurant_profile_view'),
    path('profile/edit/', views.restaurant_profile_edit, name='restaurant_profile_edit'),

    path('add_tables/', views.add_tables, name='add_tables'),
    path('tables/', views.view_tables, name='view_tables'),

    path('restaurant/<str:restaurant_code>/menu/', views.view_menu, name='view_menu'),
    path('restaurant/<str:restaurant_code>/add/', views.add_menu_item, name='add-menu-item'),
    path('restaurant/<str:restaurant_code>/edit/<int:item_id>/', views.edit_menu_item, name='edit-menu-item'),
    path('restaurant/<str:restaurant_code>/delete/<int:item_id>/', views.delete_menu_item, name='delete-menu-item'),

    path('view-orders/', views.view_orders, name='view_orders'), 
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    path('edit_table/<int:table_id>/', views.edit_table, name='edit_table'),
]

