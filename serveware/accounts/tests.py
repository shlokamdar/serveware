from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Customer, Restaurant

STRONG_PASSWORD = "Str0ngPass!23"


def make_restaurant_user(username="resto", email=None):
    user = CustomUser.objects.create_user(
        username=username, password=STRONG_PASSWORD, user_type="restaurant",
        email=email or f"{username}@example.com",
    )
    restaurant = Restaurant.objects.create(
        restaurant_admin=user,
        restaurant_name="Test Restaurant",
        restaurant_address="123 Main St",
        restaurant_pincode="560001",
        phone="9876543210",
        email=user.email,
    )
    return user, restaurant


def make_customer_user(username="cust", email=None):
    user = CustomUser.objects.create_user(
        username=username, password=STRONG_PASSWORD, user_type="customer",
        email=email or f"{username}@example.com",
    )
    Customer.objects.create(user=user, phone="9876543211")
    return user


class RestaurantSignupTests(TestCase):
    def test_signup_creates_user_and_restaurant_and_logs_in(self):
        response = self.client.post(reverse("accounts:restaurant_signup"), {
            "username": "newresto",
            "password1": STRONG_PASSWORD,
            "password2": STRONG_PASSWORD,
            "email": "newresto@example.com",
            "restaurant_name": "Test Diner",
            "restaurant_address": "123 Main St",
            "restaurant_landmark": "",
            "restaurant_pincode": "560001",
            "phone": "9876543210",
            "gst_number": "",
        })

        user = CustomUser.objects.get(username="newresto")
        self.assertEqual(user.user_type, "restaurant")
        self.assertTrue(Restaurant.objects.filter(restaurant_admin=user, restaurant_name="Test Diner").exists())
        self.assertRedirects(response, reverse("restaurant:restaurant_dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_signup_with_missing_fields_does_not_create_user(self):
        response = self.client.post(reverse("accounts:restaurant_signup"), {"username": "incomplete"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(username="incomplete").exists())


class CustomerSignupTests(TestCase):
    def test_signup_creates_user_and_profile_and_logs_in(self):
        response = self.client.post(reverse("accounts:customer_signup"), {
            "username": "newcust",
            "email": "newcust@example.com",
            "password1": STRONG_PASSWORD,
            "password2": STRONG_PASSWORD,
            "phone": "9876543210",
            "dob": "2000-01-01",
        })

        user = CustomUser.objects.get(username="newcust")
        self.assertEqual(user.user_type, "customer")
        self.assertTrue(Customer.objects.filter(user=user).exists())
        self.assertRedirects(response, reverse("customer:customer_dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)


class SignInTests(TestCase):
    def setUp(self):
        self.restaurant_user, self.restaurant = make_restaurant_user("r1")
        self.customer_user = make_customer_user("c1")

    def test_restaurant_signin_success(self):
        response = self.client.post(reverse("accounts:restaurant_signin"), {
            "username": "r1", "password": STRONG_PASSWORD,
        })
        self.assertRedirects(response, reverse("restaurant:restaurant_dashboard"))

    def test_restaurant_signin_rejects_customer_account(self):
        response = self.client.post(reverse("accounts:restaurant_signin"), {
            "username": "c1", "password": STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_signin_success(self):
        response = self.client.post(reverse("accounts:customer_signin"), {
            "username": "c1", "password": STRONG_PASSWORD,
        })
        self.assertRedirects(response, reverse("customer:customer_dashboard"))

    def test_customer_signin_rejects_restaurant_account(self):
        response = self.client.post(reverse("accounts:customer_signin"), {
            "username": "r1", "password": STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_signin_wrong_password_fails(self):
        response = self.client.post(reverse("accounts:restaurant_signin"), {
            "username": "r1", "password": "totally-wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class PasswordResetFlowTests(TestCase):
    """Covers the happy path of forgot_password -> verify_otp -> reset_password.

    Note: reset_password's authorization behavior (whether it correctly
    requires a verified OTP for the given user_id) is intentionally left
    untouched and untested here per the scope of this change.
    """

    def setUp(self):
        self.user, self.restaurant = make_restaurant_user("r2")

    def test_forgot_password_sends_otp_and_redirects(self):
        response = self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})

        self.assertRedirects(response, reverse("accounts:verify_otp"))
        self.assertIn("otp", self.client.session)
        self.assertEqual(self.client.session["request_user"], self.user.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.client.session["otp"], mail.outbox[0].body)

    def test_forgot_password_unknown_email_shows_error(self):
        response = self.client.post(reverse("accounts:forgot_password"), {"email": "nobody@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_otp_correct_redirects_to_reset(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        otp = self.client.session["otp"]

        response = self.client.post(reverse("accounts:verify_otp"), {"otp": otp})

        self.assertRedirects(response, reverse("accounts:reset_password", args=[self.user.id]))

    def test_verify_otp_incorrect_shows_error_and_keeps_session(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})

        response = self.client.post(reverse("accounts:verify_otp"), {"otp": "wrong0"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("otp", self.client.session)

    def test_reset_password_with_matching_passwords_updates_password(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        otp = self.client.session["otp"]
        self.client.post(reverse("accounts:verify_otp"), {"otp": otp})

        response = self.client.post(reverse("accounts:reset_password", args=[self.user.id]), {
            "new_password": "BrandNewPass!99",
            "confirm_new_password": "BrandNewPass!99",
        })

        self.assertRedirects(response, reverse("accounts:restaurant_signin"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPass!99"))
        self.assertNotIn("otp", self.client.session)

    def test_reset_password_with_mismatched_passwords_does_not_update(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.user.email})
        otp = self.client.session["otp"]
        self.client.post(reverse("accounts:verify_otp"), {"otp": otp})

        response = self.client.post(reverse("accounts:reset_password", args=[self.user.id]), {
            "new_password": "BrandNewPass!99",
            "confirm_new_password": "SomethingElse!1",
        })

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))
