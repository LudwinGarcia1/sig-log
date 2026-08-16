from django import forms
from django.test import TestCase, override_settings
from django.urls import include, path, reverse

from apps.core.navigation import NAV_ITEMS
from apps.core.views import CrudConfig, HomeView
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


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("widgets/", include(WidgetCrud.urlpatterns())),
]


@override_settings(ROOT_URLCONF="apps.core.tests.test_crud")
class CrudEngineTest(TestCase):
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
        # This test overrides ROOT_URLCONF to a minimal urlconf that only
        # knows about "home" and the widget routes. Other catalog modules
        # register their own entries into the process-global NAV_ITEMS as
        # soon as the real ROOT_URLCONF is imported (e.g. by URL system
        # checks), and base.html renders every registered entry regardless
        # of which urlconf is active. Isolate this test from that global
        # state so it only exercises the routes it declares.
        self._original_nav_items = list(NAV_ITEMS)
        NAV_ITEMS.clear()
        Widget.objects.create(code="W-01", name="Tornillo", size="SMALL")
        Widget.objects.create(code="W-02", name="Palanca", size="LARGE")

    def tearDown(self):
        NAV_ITEMS.clear()
        NAV_ITEMS.extend(self._original_nav_items)

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
