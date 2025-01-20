from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from accounts.forms import (
    RestaurantSignUpForm, CustomerSignInForm, 
    RestaurantSignInForm, CustomerRegistrationForm, PasswordResetEmailForm, 
    SetNewPasswordForm
)
from accounts.models import CustomUser, Customer
import secrets


def home(request):
    return render(request, 'home.html')


def join_restaurant(request):
    return render(request, 'accounts/join_restaurant.html')


def join_customer(request):
    return render(request, 'accounts/join_customer.html')


def restaurant_signup(request):
    if request.method == 'POST':
        form = RestaurantSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('restaurant:restaurant_dashboard')
        else:
            messages.error(request, "There was an error with your restaurant sign-up. Please check the details and try again.")
    else:
        form = RestaurantSignUpForm()
    return render(request, 'accounts/restaurant_signup.html', {'form': form})


def customer_register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'customer'
            user.save()
            login(request, user)
            Customer.objects.create(user=user, phone=form.cleaned_data['phone'], dob=form.cleaned_data['dob'])
            messages.success(request, 'Your account has been created successfully! You are now logged in.')
            return redirect('customer:customer_dashboard')
        else:
            messages.error(request, 'There was an error with your form. Please try again.')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'accounts/customer_signup.html', {'form': form})



def restaurant_signin(request):
    if request.method == 'POST':
        form = RestaurantSignInForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('restaurant:restaurant_dashboard')
    else:
        form = RestaurantSignInForm()
    return render(request, 'accounts/restaurant_signin.html', {'form': form})



def customer_signin(request):
    if request.method == 'POST':
        form = CustomerSignInForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('customer:customer_dashboard')
    else:
        form = CustomerSignInForm()
    return render(request, 'accounts/customer_signin.html', {'form': form})


def generate_otp(user):
    otp = secrets.token_hex(3)
    return otp


def forgot_password(request):
    if request.method == "POST":
        form = PasswordResetEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                otp = generate_otp(user)
                request.session['otp'] = otp
                request.session['request_user'] = user.id
                send_mail(
                    'Password Reset OTP',
                    f'OTP to reset your password is: {otp}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False
                )
                return redirect('accounts:verify_otp')
            except CustomUser.DoesNotExist:
                messages.error(request, "No user found with this email.")
        else:
            messages.error(request, "Please provide a valid email address.")
    else:
        form = PasswordResetEmailForm()
    return render(request, "accounts/forgot_password.html", {'form': form})


def verify_otp(request):
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        otp_stored = request.session.get('otp')
        if otp_entered == otp_stored:
            user_id = request.session.get('request_user')
            if user_id:
                return redirect('accounts:reset_password', user_id=user_id)
            else:
                messages.error(request, "Session expired. Please request OTP again.")
                return redirect('forgot_password')
        else:
            messages.error(request, "Invalid OTP.")
    return render(request, 'accounts/verify_otp.html')


from django.contrib.auth import get_user_model


CustomUser = get_user_model()  
def reset_password(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('error_page')

    if request.method == 'POST':
        form = SetNewPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            request.session.pop('otp', None)
            request.session.pop('request_user', None)
            messages.success(request, "Your password has been reset successfully.")

            # Redirect to the respective sign-in page based on user_type
            if user.user_type == 'restaurant':
                return redirect('accounts:restaurant_signin')
            elif user.user_type == 'customer':
                return redirect('accounts:customer_signin')
        else:
            messages.error(request, "There was an error with your form. Please try again.")
    else:
        form = SetNewPasswordForm(user=user)

    return render(request, 'accounts/reset_password.html', {'form': form})



def custom_logout(request):
    logout(request)
    return redirect('/')
