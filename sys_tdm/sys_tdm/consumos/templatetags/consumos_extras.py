from django import template

register = template.Library()

@register.filter
def get_verbose_name(obj):
    if hasattr(obj, '_meta'):
        return obj._meta.verbose_name
    return obj
