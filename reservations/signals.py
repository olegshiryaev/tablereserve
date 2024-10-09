from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Reservation
from .utils import inflect_word, format_russian_date


def send_reservation_email(subject, message, recipient_email):
    """Отправка email с уведомлением о бронировании."""
    send_mail(
        subject=subject,
        message=message,
        from_email="info@rezerve.group",  # Можно заменить на актуальный email отправителя
        recipient_list=[recipient_email],
        fail_silently=False,
        html_message=message,
    )


@receiver(post_save, sender=Reservation)
def send_reservation_notifications(sender, instance, created, **kwargs):
    """Отправляет уведомления клиенту и заведению при создании/изменении бронирования."""
    # Отправляем уведомления клиенту
    send_reservation_email_to_customer(instance, created)

    # Отправляем уведомления заведению
    send_reservation_email_to_place(instance, created)


def send_reservation_email_to_customer(instance, created):
    """Отправка уведомления клиенту о бронировании."""

    # Форматируем дату и время
    formatted_date = format_russian_date(instance.date)
    formatted_time = instance.time.strftime("%H:%M")

    # Получаем email клиента (если есть пользователь, берем его email)
    recipient_email = (
        instance.customer_email if not instance.user else instance.user.email
    )

    # Проверяем наличие столика и зала
    zone_info = (
        f"Зона: {instance.table.hall.name}<br>"
        if instance.table and instance.table.hall
        else "Зона: Не выбрана<br>"
    )
    table_info = (
        f"Столик: {instance.table}<br>" if instance.table else "Столик: Любой<br>"
    )

    if created:
        # Уведомление клиенту при создании бронирования
        send_reservation_email(
            subject=f"Заявка на Бронирование №{instance.number} отправлена",
            message=(
                f"Ваша заявка на Бронирование №{instance.number} принята в работу.<br>"
                f"<strong>Детали заявки:</strong><br>"
                f"Ресторан: {instance.place.name}<br>"
                f"Адрес: {instance.place.address}<br>"
                f"Тел.: {instance.place.phone}<br>"
                f"{zone_info}"
                f"{table_info}"
                f"Дата: {formatted_date}<br>"
                f"Время: {formatted_time}<br><br>"
                f"Ожидайте подтверждения.<br><br>"
                f"<strong>С уважением,<br>"
                f"Сервис онлайн-бронирования столиков «RESERVE»<br>"
                f"www.reserve.cafe</strong>"
            ),
            recipient_email=recipient_email,
        )
    else:
        # Уведомление клиенту при изменении статуса бронирования
        if instance.status == "confirmed":
            send_reservation_confirmed_email_to_customer(instance, recipient_email)
        elif instance.status in ["cancelled_by_restaurant", "cancelled_by_customer"]:
            send_reservation_cancelled_email_to_customer(instance, recipient_email)


def send_reservation_confirmed_email_to_customer(instance, recipient_email):
    """Уведомление клиента о подтверждении бронирования."""

    # Форматируем дату и время
    formatted_date = format_russian_date(instance.date)
    formatted_time = instance.time.strftime("%H:%M")

    # Получаем падежное окончание для типа заведения
    place_type_name = inflect_word(instance.place.type.name, "loct")

    # Проверяем наличие столика и зала
    zone_info = (
        f"Зона: {instance.table.hall.name}<br>"
        if instance.table and instance.table.hall
        else "Зона: Не выбрана<br>"
    )
    table_info = (
        f"Столик: {instance.table}<br>" if instance.table else "Столик: Любой<br>"
    )

    send_reservation_email(
        subject=f"Бронирование №{instance.number} Подтверждено",
        message=(
            f"Ваше Бронирование №{instance.number} подтверждено.<br>"
            f"<strong>Детали заявки:</strong><br>"
            f"Ресторан: {instance.place.name}<br>"
            f"Адрес: {instance.place.address}<br>"
            f"Тел.: {instance.place.phone}<br>"
            f"{zone_info}"
            f"{table_info}"
            f"Дата: {formatted_date}<br>"
            f"Время: {formatted_time}<br><br>"
            f"Желаем Вам приятно провести время.<br><br>"
            f"<strong>С уважением,<br>"
            f"Сервис онлайн-бронирования столиков «RESERVE»<br>"
            f"www.reserve.cafe</strong>"
        ),
        recipient_email=recipient_email,
    )


def send_reservation_cancelled_email_to_customer(instance, recipient_email):
    """Уведомление клиента об отмене бронирования."""
    send_reservation_email(
        subject=f"Бронирование №{instance.number} Отменено",
        message=f"Ваше Бронирование №{instance.number} отменено.",
        recipient_email=recipient_email,
    )


def send_reservation_email_to_place(instance, created):
    """Отправка уведомления на email заведения."""
    # Получаем email заведения из настроек бронирования (BookingSettings)
    notification_email = instance.place.booking_settings.notification_email

    if notification_email:
        if created:
            # Уведомление заведению о новом бронировании
            send_new_reservation_email_to_place(instance, notification_email)
        else:
            # Уведомление заведению об изменении статуса бронирования
            send_reservation_status_update_email_to_place(instance, notification_email)


def send_new_reservation_email_to_place(instance, notification_email):
    """Уведомление заведения о новом бронировании."""

    # Форматируем дату и время
    formatted_date = format_russian_date(instance.date)
    formatted_time = instance.time.strftime("%H:%M")

    # Проверяем наличие столика и зала
    zone_info = (
        f"<strong>Зона:</strong> {instance.table.hall.name}<br>"
        if instance.table and instance.table.hall
        else "<strong>Зона:</strong> Не выбрана<br>"
    )
    table_info = (
        f"<strong>Столик:</strong> {instance.table}<br>"
        if instance.table
        else "<strong>Столик:</strong> Любой<br>"
    )
    send_reservation_email(
        subject=f"Новое бронирование столика в {instance.place.name}",
        message=(
            f"<p><strong>Новое бронирование столика в {instance.place.name}:</strong></p>"
            f"<p><strong>Бронь №:</strong> {instance.number}<br>"
            f"<strong>Имя клиента:</strong> {instance.customer_name}<br>"
            f"<strong>Телефон:</strong> {instance.customer_phone}<br>"
            f"<strong>Дата:</strong> {formatted_date}<br>"
            f"<strong>Время:</strong> {formatted_time}<br>"
            f"{zone_info}"
            f"{table_info}"
            f"<strong>Количество гостей:</strong> {instance.guests}<br>"
            f"<strong>Пожелания:</strong> {instance.wishes or 'Нет'}</p>"
        ),
        recipient_email=notification_email,
    )


def send_reservation_status_update_email_to_place(instance, notification_email):
    """Уведомление заведения об изменении статуса бронирования."""
    if instance.status == "confirmed":
        send_reservation_confirmed_email_to_place(instance, notification_email)
    elif instance.status in ["cancelled_by_restaurant", "cancelled_by_customer"]:
        send_reservation_cancelled_email_to_place(instance, notification_email)


def send_reservation_confirmed_email_to_place(instance, notification_email):
    """Уведомление заведения о подтверждении бронирования."""

    # Форматируем дату и время
    formatted_date = format_russian_date(instance.date)
    formatted_time = instance.time.strftime("%H:%M")

    # Определяем зону и столик, если они указаны
    hall_name = (
        instance.table.hall.name
        if instance.table and instance.table.hall
        else "Не выбрана"
    )
    table_name = instance.table.name if instance.table else "Любой"

    # Подготовка и отправка письма
    send_reservation_email(
        subject=f"Бронирование №{instance.number} подтверждено",
        message=(
            f"<p><strong>Бронирование №{instance.number} подтверждено.</strong></p>"
            f"<p><strong>Дата:</strong> {formatted_date}<br>"
            f"<strong>Время:</strong> {formatted_time}<br>"
            f"<strong>Количество гостей:</strong> {instance.guests}<br>"
            f"<strong>Имя клиента:</strong> {instance.customer_name}<br>"
            f"<strong>Телефон клиента:</strong> {instance.customer_phone}<br>"
            f"<strong>Зона:</strong> {hall_name}<br>"
            f"<strong>Столик:</strong> {table_name}<br>"
            f"<strong>Пожелания клиента:</strong> {instance.wishes or 'Нет'}</p>"
        ),
        recipient_email=notification_email,
    )


def send_reservation_cancelled_email_to_place(instance, notification_email):
    """Уведомление заведения об отмене бронирования."""
    send_reservation_email(
        subject=f"Бронирование №{instance.number} отменено",
        message=f"Бронирование №{instance.number} было отменено.",
        recipient_email=notification_email,
    )
