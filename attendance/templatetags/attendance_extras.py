from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dict by key in templates."""
    return dictionary.get(key)
