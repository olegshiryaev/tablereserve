from django import template
import re
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


@register.filter(name="add_class")
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


@register.filter
def is_checkbox_select_multiple(field):
    return isinstance(field.field.widget, CheckboxSelectMultiple)


@register.filter
def split_list(value, chunk_size):
    # Преобразуем значение в список, если оно не является списком
    if hasattr(value, "__iter__") and not isinstance(value, list):
        value = list(value)
    if not isinstance(value, list):
        raise ValueError("split_list filter expects a list.")

    chunk_size = int(chunk_size)
    return [value[i : i + chunk_size] for i in range(0, len(value), chunk_size)]


@register.filter
def range_filter(value, arg):
    """
    Возвращает диапазон от `value` до `arg`
    """
    return range(value, arg)


@register.filter
def format_phone_number(value):
    if not value:
        return ""
    # Удаляем все нецифровые символы
    value = re.sub(r"\D", "", value)
    if len(value) == 11:
        return f"+7 ({value[1:4]}) {value[4:7]} {value[7:9]} {value[9:]}"
    return value
