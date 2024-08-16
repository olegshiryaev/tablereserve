from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_password_email(email, password):
    subject = "Ваш новый пароль"
    html_message = render_to_string(
        "emails/new_account_password.html", {"password": password}
    )
    send_mail(
        subject,
        None,  # Текстовое сообщение не используется
        "oashiryaev@yandex.ru",
        [email],
        html_message=html_message,
    )
