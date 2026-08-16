from django import template

register = template.Library()


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
