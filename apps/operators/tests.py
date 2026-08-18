from datetime import date, timedelta

from django.test import TestCase

from apps.operators.models import Operator


class OperatorBehaviourTest(TestCase):
    def _operator(self, **overrides):
        defaults = {
            "employee_number": "OP-0001",
            "first_name": "Ana",
            "last_name": "Ruiz",
            "license_number": "LF-99887",
            "license_type": "B",
            "license_expiry": date.today() + timedelta(days=365),
            "hire_date": date.today() - timedelta(days=365 * 3 + 10),
            "phone": "5512345678",
        }
        defaults.update(overrides)
        return Operator.objects.create(**defaults)

    def test_full_name_joins_first_and_last(self):
        self.assertEqual(self._operator().full_name, "Ana Ruiz")

    def test_license_is_valid_when_expiry_is_future(self):
        self.assertTrue(self._operator().license_is_valid)

    def test_license_is_invalid_when_expired(self):
        operator = self._operator(license_expiry=date.today() - timedelta(days=1))
        self.assertFalse(operator.license_is_valid)

    def test_seniority_years_counts_completed_years(self):
        self.assertEqual(self._operator().seniority_years, 3)

    def test_seniority_years_is_zero_when_hired_today(self):
        operator = self._operator(hire_date=date.today())
        self.assertEqual(operator.seniority_years, 0)

    def test_seniority_years_is_not_negative_when_hire_date_is_future(self):
        operator = self._operator(hire_date=date.today() + timedelta(days=30))
        self.assertEqual(operator.seniority_years, 0)
