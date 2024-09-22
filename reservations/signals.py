from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Reservation
from .utils import inflect_word, format_russian_date


def send_reservation_email(subject, message, recipient_email):
    send_mail(
        subject=subject,
        message=message,
        from_email="info@rezerve.group",
        recipient_list=[recipient_email],
        fail_silently=False,
    )


@receiver(post_save, sender=Reservation)
def send_reservation_status_email(sender, instance, created, **kwargs):
    profile = instance.user.profile if instance.user else None

    if profile and not profile.email_notifications:
        return  # Если уведомления выключены, ничего не делаем

    recipient_email = (
        instance.customer_email if not instance.user else instance.user.email
    )

    if created:
        # Уведомление при создании заказа
        send_reservation_email(
            subject=f"Ваш заказ №{instance.number} принят в работу",
            message=f"Ваш заказ №{instance.number} принят в работу. Ожидайте подтверждения.",
            recipient_email=recipient_email,
        )
    else:
        # Уведомления при изменении статуса
        if instance.status == "confirmed":
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
        elif instance.status in ["cancelled_by_restaurant", "cancelled_by_customer"]:
            send_reservation_email(
                subject=f"Ваш заказ №{instance.number} отменён",
                message=f"Ваш заказ №{instance.number} был отменён.",
                recipient_email=recipient_email,
            )
