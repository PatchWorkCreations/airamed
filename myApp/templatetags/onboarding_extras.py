"""Small dict-access filters for the data-driven onboarding wizard templates."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if hasattr(mapping, 'get'):
        return mapping.get(key)
    return None


@register.filter
def get_list(mapping, key):
    value = mapping.get(key) if hasattr(mapping, 'get') else None
    return value if isinstance(value, list) else []
