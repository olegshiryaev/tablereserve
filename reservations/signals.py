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
    )


@receiver(post_save, sender=Reservation)
def send_reservation_notifications(sender, instance, created, **kwargs):
    """Отправляет уведомления как клиенту, так и заведению при создании/изменении бронирования."""
    # Отправляем уведомления клиенту
    send_reservation_email_to_customer(instance, created)

    # Отправляем уведомления заведению
    send_reservation_email_to_place(instance, created)


def send_reservation_email_to_customer(instance, created):
    """Отправка уведомления клиенту."""
    recipient_email = (
        instance.customer_email if not instance.user else instance.user.email
    )

    if created:
        # Уведомление клиенту при создании бронирования
        send_reservation_email(
            subject=f"Ваш заказ №{instance.number} принят в работу",
            message=f"Ваш заказ №{instance.number} принят в работу. Ожидайте подтверждения.",
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
    formatted_date = format_russian_date(instance.date)
    formatted_time = instance.time.strftime("%H:%M")
    place_type_name = inflect_word(instance.place.type.name, "loct")

    send_reservation_email(
        subject=f"Ваш заказ №{instance.number} подтверждён",
        message=(
            f"Ваш заказ №{instance.number} подтверждён. "
            f"{formatted_date} в {formatted_time} вас ждут в {place_type_name} {instance.place.name}, "
            f"по адресу: {instance.place.address}."
        ),
        recipient_email=recipient_email,
    )


def send_reservation_cancelled_email_to_customer(instance, recipient_email):
    """Уведомление клиента об отмене бронирования."""
    send_reservation_email(
        subject=f"Ваш заказ №{instance.number} отменён",
        message=f"Ваш заказ №{instance.number} был отменён.",
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
    send_reservation_email(
        subject=f"Новое бронирование столика в {instance.place.name}",
        message=(
            f"Новое бронирование столика в {instance.place.name}:\n"
            f"Имя клиента: {instance.customer_name}\n"
            f"Телефон: {instance.customer_phone}\n"
            f"Дата: {instance.date.strftime('%Y-%m-%d')}\n"
            f"Время: {instance.time.strftime('%H:%M')}\n"
            f"Количество гостей: {instance.guests}\n"
            f"Пожелания: {instance.wishes or 'Нет'}"
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
    formatted_date = format_russian_date(instance.date)
    formatted_time = instance.time.strftime("%H:%M")

    send_reservation_email(
        subject=f"Бронирование №{instance.number} подтверждено",
        message=(
            f"Бронирование №{instance.number} подтверждено.\n"
            f"Дата: {formatted_date}\n"
            f"Время: {formatted_time}\n"
            f"Количество гостей: {instance.guests}\n"
            f"Имя клиента: {instance.customer_name}\n"
            f"Телефон клиента: {instance.customer_phone}\n"
            f"Пожелания клиента: {instance.wishes or 'Нет'}"
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
