from django import forms
from django.contrib.auth import views as auth_views
from django.test import override_settings
from django.urls import include, path, reverse

from apps.core.navigation import NAV_ITEMS, register
from apps.core.views import CrudConfig, HomeView
from apps.core.tests.base import AuthenticatedTestCase
from apps.core.tests.models import Widget


class WidgetForm(forms.ModelForm):
    class Meta:
        model = Widget
        fields = ["code", "name", "size"]


class WidgetCrud(CrudConfig):
    model = Widget
    form_class = WidgetForm
    list_columns = ["code", "name", "size"]
    search_fields = ["code", "name"]
    label = "Widget"
    label_plural = "Widgets"
    slug = "widget"
    ordering = ("code",)


# base.html reverses "logout", so this reduced urlconf declares the auth
# routes too — otherwise rendering any CRUD page here raises NoReverseMatch.
urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("widgets/", include(WidgetCrud.urlpatterns())),
]


@override_settings(ROOT_URLCONF="apps.core.tests.test_crud")
class CrudEngineTest(AuthenticatedTestCase):
    """Exercises the engine that every maintenance module is built on."""

    databases = {"default"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection

        with connection.schema_editor() as editor:
            editor.create_model(Widget)

    @classmethod
    def tearDownClass(cls):
        from django.db import connection

        with connection.schema_editor() as editor:
            editor.delete_model(Widget)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        Widget.objects.create(code="W-01", name="Tornillo", size="SMALL")
        Widget.objects.create(code="W-02", name="Palanca", size="LARGE")

    def test_urlpatterns_expose_four_named_routes(self):
        names = {pattern.name for pattern in WidgetCrud.urlpatterns()}
        self.assertEqual(
            names,
            {"widget_list", "widget_create", "widget_update", "widget_delete"},
        )

    def test_list_shows_active_rows(self):
        response = self.client.get(reverse("widget_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "W-01")
        self.assertContains(response, "W-02")

    def test_list_filters_by_search_term(self):
        response = self.client.get(reverse("widget_list"), {"q": "Palanca"})
        self.assertNotContains(response, "W-01")
        self.assertContains(response, "W-02")

    def test_list_hides_inactive_rows(self):
        Widget.objects.filter(code="W-01").update(is_active=False)
        response = self.client.get(reverse("widget_list"))
        self.assertNotContains(response, "W-01")

    def test_create_persists_a_row(self):
        response = self.client.post(
            reverse("widget_create"),
            {"code": "W-03", "name": "Resorte", "size": "SMALL"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Widget.objects.filter(code="W-03").exists())

    def test_delete_is_soft(self):
        widget = Widget.objects.get(code="W-01")
        response = self.client.post(
            reverse("widget_delete", args=[widget.pk])
        )
        self.assertEqual(response.status_code, 302)
        widget.refresh_from_db()
        self.assertFalse(widget.is_active)
        self.assertTrue(Widget.objects.filter(pk=widget.pk).exists())

    def test_nav_degrades_gracefully_for_unresolvable_url_name(self):
        # This urlconf (see module top) only knows "home" and the widget
        # routes. A nav entry pointing at a name it can't resolve must be
        # skipped, not crash the page with NoReverseMatch.
        original_nav_items = list(NAV_ITEMS)
        try:
            NAV_ITEMS.clear()
            register("does_not_exist", "Módulo Fantasma")
            response = self.client.get(reverse("widget_list"))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Módulo Fantasma")
        finally:
            NAV_ITEMS.clear()
            NAV_ITEMS.extend(original_nav_items)
