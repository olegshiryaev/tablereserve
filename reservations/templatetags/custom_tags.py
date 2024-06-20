from django import template

register = template.Library()

@register.filter(name='to')
def to(value, arg):
    return range(value, arg + 1)