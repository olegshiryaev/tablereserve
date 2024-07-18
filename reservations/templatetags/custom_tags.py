from django import template

register = template.Library()


@register.filter(name="to")
def to(value, arg):
    return range(value, arg + 1)


@register.filter
def get_closing_time(schedules):
    from datetime import datetime

    today = datetime.today().weekday()
    return schedules[today].close_time if schedules else "Unknown"
