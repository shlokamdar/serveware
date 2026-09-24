import logging
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from accounts.forms import (
    CustomerRegistrationForm,
    CustomerSignInForm,
    OTPForm,
    PasswordResetEmailForm,
    RestaurantSignInForm,
    RestaurantSignUpForm,
    SetNewPasswordForm,
)
from accounts.models import CustomUser, Customer

logger = logging.getLogger("serveware")


@require_GET
def home(request):
    return render(request, "home.html")


@require_GET
def join_restaurant(request):
    return render(request, "accounts/join_restaurant.html")


@require_GET
def join_customer(request):
    return render(request, "accounts/join_customer.html")


def restaurant_signup(request):
    if request.method == "POST":
        form = RestaurantSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("restaurant:restaurant_dashboard")
        messages.error(
            request,
            "There was an error with your restaurant sign-up. Please check the details and try again.",
        )
    else:
        form = RestaurantSignUpForm()
    return render(request, "accounts/restaurant_signup.html", {"form": form})


def customer_register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = "customer"
            user.save()
            login(request, user)
            Customer.objects.create(
                user=user,
                phone=form.cleaned_data["phone"],
                dob=form.cleaned_data["dob"],
            )
            messages.success(
                request,
                "Your account has been created successfully! You are now logged in.",
            )
            return redirect("customer:customer_dashboard")
        messages.error(request, "There was an error with your form. Please try again.")
    else:
        form = CustomerRegistrationForm()
    return render(request, "accounts/customer_signup.html", {"form": form})


def restaurant_signin(request):
    if request.method == "POST":
        form = RestaurantSignInForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("restaurant:restaurant_dashboard")
    else:
        form = RestaurantSignInForm()
    return render(request, "accounts/restaurant_signin.html", {"form": form})


def customer_signin(request):
    if request.method == "POST":
        form = CustomerSignInForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("customer:customer_dashboard")
    else:
        form = CustomerSignInForm()
    return render(request, "accounts/customer_signin.html", {"form": form})


def generate_otp():
    return f"{secrets.randbelow(10**6):06d}"


def forgot_password(request):
    form = PasswordResetEmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = CustomUser.objects.filter(email__iexact=email).first()
        if user:
            otp = generate_otp()
            request.session["reset_otp"] = otp
            request.session["reset_user_id"] = user.id
            request.session["reset_otp_created"] = int(time.time())
            request.session.pop("otp_verified_user_id", None)
            send_mail(
                "ServeWare password reset code",
                f"Your code is {otp}. It expires in 10 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
        # Same response whether or not the email exists (no account enumeration)
        messages.info(request, "If that email is registered, a code has been sent.")
        return redirect("accounts:verify_otp")
    return render(request, "accounts/forgot_password.html", {"form": form})


def verify_otp(request):
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expected = request.session.get("reset_otp")
        created = request.session.get("reset_otp_created", 0)
        expired = time.time() - created > settings.OTP_TTL_SECONDS
        if expected and not expired and secrets.compare_digest(form.cleaned_data["otp"], expected):
            user_id = request.session["reset_user_id"]
            request.session["otp_verified_user_id"] = user_id
            request.session.pop("reset_otp", None)
            return redirect("accounts:reset_password", user_id=user_id)
        messages.error(request, "Invalid or expired code.")
    return render(request, "accounts/verify_otp.html", {"form": form})


def reset_password(request, user_id):
    if request.session.get("otp_verified_user_id") != user_id:
        logger.warning("Blocked password reset attempt for user_id=%s without verified OTP", user_id)
        messages.error(request, "Please verify your code first.")
        return redirect("accounts:forgot_password")
    user = get_object_or_404(CustomUser, id=user_id)
    form = SetNewPasswordForm(user=user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["new_password"])
        user.save()
        for key in ("otp_verified_user_id", "reset_user_id", "reset_otp_created"):
            request.session.pop(key, None)
        messages.success(request, "Password updated. Please sign in.")
        signin = "accounts:restaurant_signin" if user.user_type == "restaurant" else "accounts:customer_signin"
        return redirect(signin)
    return render(request, "accounts/reset_password.html", {"form": form})


@require_POST
def custom_logout(request):
    logout(request)
    return redirect("home")
