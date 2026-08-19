"""Access control: the whole system lives behind a session."""

from django.test import TestCase
from django.urls import reverse

from apps.core.tests.base import TEST_PASSWORD, TEST_USERNAME, create_test_user

LOGIN_PATH = "/entrar/"

# Every screen a visitor could try to reach directly.
PROTECTED_VIEWS = [
    "home",
    "customer_list", "customer_create",
    "vehicle_list", "operator_list", "route_list",
    "delivery_list", "fuelload_list", "maintenance_list",
    "analytics_dashboard", "analytics_operations", "analytics_costs",
    "analytics_alerts", "analytics_predictions", "analytics_clusters",
]


class LoginScreenTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_the_login_screen_renders(self):
        response = self.client.get(LOGIN_PATH)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar sesión")

    def test_valid_credentials_land_on_the_home_screen(self):
        response = self.client.post(
            LOGIN_PATH, {"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        self.assertRedirects(response, reverse("home"))

    def test_invalid_credentials_stay_on_the_form(self):
        response = self.client.post(
            LOGIN_PATH, {"username": TEST_USERNAME, "password": "equivocada"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar sesión")

    def test_logging_out_returns_to_the_login_screen(self):
        self.client.force_login(self.user)
        response = self.client.post("/salir/")
        self.assertRedirects(response, LOGIN_PATH)

    def test_the_navigation_bar_is_hidden_before_logging_in(self):
        response = self.client.get(LOGIN_PATH)
        self.assertNotContains(response, "Reportes")


class AnonymousAccessTest(TestCase):
    def test_every_screen_redirects_an_anonymous_visitor(self):
        for name in PROTECTED_VIEWS:
            with self.subTest(view=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302, name)
                self.assertTrue(response.url.startswith(LOGIN_PATH), name)

    def test_the_redirect_remembers_where_the_visitor_was_going(self):
        target = reverse("analytics_costs")
        response = self.client.get(target)
        self.assertEqual(response.url, f"{LOGIN_PATH}?next={target}")

    def test_exports_are_protected_too(self):
        response = self.client.get(
            reverse("analytics_export", args=["rutas", "csv"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(LOGIN_PATH))

    def test_recording_an_arrival_is_protected(self):
        response = self.client.get(reverse("delivery_arrival", args=[1]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(LOGIN_PATH))


class AuthenticatedAccessTest(TestCase):
    def setUp(self):
        self.client.force_login(create_test_user())

    def test_the_home_screen_greets_the_user_and_offers_logout(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, TEST_USERNAME)
        self.assertContains(response, "Salir")

    def test_the_navigation_bar_lists_the_modules(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Reportes")
        self.assertContains(response, "Clientes")
