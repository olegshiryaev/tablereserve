from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.models import EmailAddress
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from dashboard.utils import send_password_email

from django.contrib.auth.signals import user_logged_in
from django.shortcuts import redirect


# @receiver(post_save, sender=EmailAddress)
# def send_password_after_email_confirmation(sender, instance, **kwargs):
#     # Проверяем, подтвержден ли email
#     if instance.verified:
#         user = instance.user
#         # Проверяем, был ли уже отправлен пароль
#         if not user.password_sent:
#             password = get_random_string(length=8)
#             user.set_password(password)
#             user.save()

#             # Отправка email с паролем
#             send_password_email(user.email, password)

#             # Устанавливаем флаг, чтобы избежать повторной отправки пароля
#             user.password_sent = True
#             user.save()
