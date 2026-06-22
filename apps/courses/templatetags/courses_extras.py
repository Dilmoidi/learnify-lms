from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(dictionary, key):
    if dictionary is None:
        return None
    # Django IDs are typically integers, key might be integer
    try:
        return dictionary.get(key)
    except (AttributeError, KeyError):
        return None
