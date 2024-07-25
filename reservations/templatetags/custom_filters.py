from django import template
from django.forms.widgets import CheckboxSelectMultiple

register = template.Library()


@register.filter
def rating_color(value):
    if value >= 4.5:
        return "green-bright"
    elif value >= 4.0:
        return "green-light"
    elif value >= 3.0:
        return "orange"
    elif value < 3:
        return "red"
    else:
        return ""


@register.filter
def review_word(count):
    if 11 <= count % 100 <= 19:
        return "отзывов"
    last_digit = count % 10
    if last_digit == 1:
        return "отзыв"
    elif 2 <= last_digit <= 4:
        return "отзыва"
    else:
        return "отзывов"


@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


@register.filter
def is_checkbox_select_multiple(field):
    return isinstance(field.field.widget, CheckboxSelectMultiple)
