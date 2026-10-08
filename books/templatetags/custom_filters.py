from django import template

register = template.Library()

@register.filter
def split(value, key):
    """يفصل النص حسب المفتاح ويعيد قائمة"""
    if value:
        return value.split(key)
    return []
