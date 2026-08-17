from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag
def nav_url(url_name):
    """Resolve a navigation entry's URL, degrading gracefully.

    A module may register a nav entry whose URL name is not resolvable
    under the urlconf currently in effect (e.g. a partial urlconf used in
    tests, or a renamed/removed route). Returning "" instead of raising lets
    the caller skip rendering that entry rather than 500ing the whole page.
    """
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return ""


@register.filter
def attr(obj, name):
    """Look up an arbitrary attribute/property on an object for template use.

    Backs the ``show_if`` hook on ``CrudConfig.extra_actions``: the attribute
    name is data, not known ahead of time, so plain dot-lookup in the
    template won't do.
    """
    return getattr(obj, name, False)


@register.simple_tag
def column_value(instance, field_name):
    """Resolve a column for the generic list template.

    Prefers Django's ``get_<field>_display`` so choice fields render their
    Spanish label instead of the stored English constant.
    """
    display = getattr(instance, f"get_{field_name}_display", None)
    value = display() if callable(display) else getattr(instance, field_name, "")
    if value is None:
        return ""
    if value is True:
        return "Sí"
    if value is False:
        return "No"
    return value
