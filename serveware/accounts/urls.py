from django.urls import path
from accounts import views
app_name  = 'accounts'

urlpatterns = [
    # Sign-Up URLs
    path('restaurant/signup/', views.restaurant_signup, name='restaurant_signup'),
    path('customer/register/', views.customer_register, name='customer_signup'),

    # Sign-In URLs
    path('restaurant/signin/', views.restaurant_signin, name='restaurant_signin'),
    path('customer/signin/', views.customer_signin, name='customer_signin'),

    # Join URLs
    path('join-restaurant/', views.join_restaurant, name='join_restaurant'),
    path('join-customer/', views.join_customer, name='join_customer'),

    # Forgot Password URLs
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),

    # Logout URL
    path('logout/', views.custom_logout, name='logout'),
]
