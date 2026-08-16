from django.db import models
from django.test import TestCase

from apps.core.models import BaseModel


class BaseModelFieldsTest(TestCase):
    def test_base_model_is_abstract(self):
        self.assertTrue(BaseModel._meta.abstract)

    def test_base_model_declares_audit_fields(self):
        field_names = {field.name for field in BaseModel._meta.get_fields()}
        self.assertEqual(field_names, {"created_at", "updated_at", "is_active"})

    def test_is_active_defaults_to_true(self):
        field = BaseModel._meta.get_field("is_active")
        self.assertIsInstance(field, models.BooleanField)
        self.assertTrue(field.default)
