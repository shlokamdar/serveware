from datetime import date

from django.core import mail
from django.urls import reverse

from testutils import PASSWORD, ServeWareTestCase, make_customer, make_restaurant_owner


class HealthCheckTests(ServeWareTestCase):
    def test_healthz_returns_ok_json(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_fault_injection_disabled_by_default(self):
        self.assertEqual(self.client.get(reverse("simulate_error")).status_code, 404)

    def test_metrics_endpoint_exposed(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"django_http", response.content)


class CustomerModelTests(ServeWareTestCase):
    def test_is_birthday_true_on_matching_day(self):
        user = make_customer()
        today = date.today()
        user.customer_profile.dob = date(2000, today.month, min(today.day, 28))
        if today.day <= 28:
            self.assertTrue(user.customer_profile.is_birthday)


class RoleSeparationTests(ServeWareTestCase):
    def test_customer_cannot_open_restaurant_dashboard(self):
        customer = make_customer()
        self.client.login(username=customer.username, password=PASSWORD)
        response = self.client.get(reverse("restaurant:restaurant_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_restaurant_owner_cannot_open_customer_dashboard(self):
        owner, _ = make_restaurant_owner()
        self.client.login(username=owner.username, password=PASSWORD)
        response = self.client.get(reverse("customer:customer_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected_to_signin(self):
        response = self.client.get(reverse("restaurant:restaurant_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("signin", response["Location"])


class PasswordResetSecurityTests(ServeWareTestCase):
    def setUp(self):
        self.owner, _ = make_restaurant_owner()

    def test_forgot_password_sends_otp_email(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.owner.email})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset_otp", self.client.session)

    def test_unknown_email_does_not_crash_or_send(self):
        response = self.client.post(reverse("accounts:forgot_password"), {"email": "nobody@test.local"})
        self.assertIn(response.status_code, (200, 302))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_without_verified_otp_is_blocked(self):
        url = reverse("accounts:reset_password", args=[self.owner.id])
        response = self.client.post(
            url,
            {"new_password": "Hacked-Pass-1!", "confirm_new_password": "Hacked-Pass-1!"},
        )
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(PASSWORD))

    def test_wrong_otp_is_rejected(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.owner.email})
        self.client.post(reverse("accounts:verify_otp"), {"otp": "000000x"})
        self.assertNotIn("otp_verified_user_id", self.client.session)

    def test_full_reset_flow_with_valid_otp(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": self.owner.email})
        otp = self.client.session["reset_otp"]
        self.client.post(reverse("accounts:verify_otp"), {"otp": otp})
        new = "Brand-New-Pass-9!"
        self.client.post(
            reverse("accounts:reset_password", args=[self.owner.id]),
            {"new_password": new, "confirm_new_password": new},
        )
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(new))
