from django.utils import timezone
from datetime import timedelta


def get_avatar_upload_path(instance, filename):
    base_path = "images/avatars"
    return f"{base_path}/{instance.user.id}/{filename}"


def is_online(user):
    if user.last_activity:
        now = timezone.now()
        if (now - user.last_activity).total_seconds() < 300:  # 5 минут
            return True
    return False


def time_since_last_seen(user):
    """
    Возвращает сообщение о том, сколько времени прошло с момента последней активности пользователя
    """
    if not user.last_activity:
        return "Нет данных о последней активности"

    now = timezone.now()
    time_difference = now - user.last_activity

    if time_difference < timedelta(minutes=5):
        return "Онлайн"

    # Определяем время в днях, месяцах и годах
    days = time_difference.days
    seconds = time_difference.seconds

    if days > 365:
        years = days // 365
        return (
            f"Был(а) {years} год(а) назад"
            if years == 1
            else f"Был(а) {years} лет назад"
        )
    elif days > 30:
        months = days // 30
        return (
            f"Был(а) {months} месяц назад"
            if months == 1
            else f"Был(а) {months} месяцев назад"
        )
    elif days > 0:
        return f"Был(а) {days} день назад" if days == 1 else f"Был(а) {days} дней назад"
    elif seconds >= 3600:
        hours = seconds // 3600
        return (
            f"Был(а) {hours} час назад" if hours == 1 else f"Был(а) {hours} часов назад"
        )
    elif seconds >= 60:
        minutes = seconds // 60
        return (
            f"Был(а) {minutes} минуту назад"
            if minutes == 1
            else f"Был(а) {minutes} минут назад"
        )
    else:
        return "Был(а) только что"
