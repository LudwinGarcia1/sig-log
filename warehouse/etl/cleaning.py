"""One named function per cleaning rule.

Naming each rule is what lets ``dw.etl_error.rule`` say *why* a row was
quarantined, and what makes the techniques of Unidad II auditable one by one.
"""

import re
from decimal import Decimal

EFFICIENCY_BOUNDS = (Decimal("1.0"), Decimal("8.0"))
UNKNOWN_TEXT = "DESCONOCIDA"
UNSPECIFIED_CAUSE = "NO_ESPECIFICADA"

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def normalize_text(value):
    """Trim, collapse inner whitespace and title-case a free-text field."""
    if value is None:
        return ""
    return _WHITESPACE.sub(" ", str(value).strip()).title()


def normalize_code(value):
    """Uppercase identifier with surrounding whitespace removed."""
    if value is None:
        return ""
    return str(value).strip().upper()


def normalize_plate(value):
    """Uppercase plate with hyphens, dots and spaces removed."""
    if value is None:
        return ""
    return _NON_ALNUM.sub("", str(value)).upper()


def default_if_blank(value, fallback=UNKNOWN_TEXT):
    """Replace an empty or whitespace-only value with an explicit marker."""
    if value is None or not str(value).strip():
        return fallback
    return value


def is_positive(value):
    return value is not None and Decimal(value) > 0


def is_non_negative(value):
    return value is not None and Decimal(value) >= 0


def dates_are_coherent(departure, arrival):
    """An arrival may be missing, but it may never precede the departure."""
    if departure is None:
        return False
    if arrival is None:
        return True
    return arrival >= departure


def is_efficiency_outlier(value):
    if value is None:
        return False
    low, high = EFFICIENCY_BOUNDS
    return not (low <= Decimal(value) <= high)


def age_range(year, reference_year):
    age = max(reference_year - int(year), 0)
    if age <= 3:
        return "0-3"
    if age <= 8:
        return "4-8"
    return "9+"


def distance_range(km):
    kilometres = Decimal(km)
    if kilometres < Decimal("80"):
        return "CORTA"
    if kilometres < Decimal("350"):
        return "MEDIA"
    return "LARGA"


def capacity_range(kg):
    kilograms = Decimal(kg)
    if kilograms < Decimal("2000"):
        return "LIGERA"
    if kilograms < Decimal("15000"):
        return "MEDIANA"
    return "PESADA"


def seniority_range(hire_date, today):
    years = today.year - hire_date.year
    if (today.month, today.day) < (hire_date.month, hire_date.day):
        years -= 1
    years = max(years, 0)
    if years <= 2:
        return "0-2"
    if years <= 5:
        return "3-5"
    return "6+"
