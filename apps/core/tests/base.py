"""Shared scaffolding for view tests, now that every screen needs a session.

Test classes that drive ``self.client`` against a protected view inherit from
``AuthenticatedTestCase`` instead of ``TestCase``: it creates a user and opens
the session in ``setUp``, so the assertions stay about the module under test
rather than about logging in.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

TEST_USERNAME = "operador_pruebas"
TEST_PASSWORD = "clave-de-pruebas"


def create_test_user(username=TEST_USERNAME, password=TEST_PASSWORD):
    return get_user_model().objects.create_user(username=username, password=password)


class AuthenticatedTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = create_test_user()
        self.client.force_login(self.user)
