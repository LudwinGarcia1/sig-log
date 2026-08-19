from django.urls import reverse

from apps.core.tests.base import AuthenticatedTestCase
from apps.customers.models import Customer


class CustomerCrudTest(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        Customer.objects.create(
            code="CLI-0001",
            business_name="Distribuidora del Valle",
            tax_id="DVA010203AB1",
            contact_name="Luis Mora",
            phone="7221234567",
            email="luis@dvalle.mx",
            address="Av. Reforma 100",
            city="Toluca",
            state="México",
            postal_code="50000",
            customer_type="PREMIUM",
        )

    def test_list_renders_customer(self):
        response = self.client.get(reverse("customer_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Distribuidora del Valle")

    def test_customer_type_renders_spanish_label(self):
        response = self.client.get(reverse("customer_list"))
        self.assertContains(response, "Premium")
