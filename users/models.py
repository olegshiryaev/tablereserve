from django.conf import settings
from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone

from reservations.models import Place


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Поле "Электронная почта" должно быть заполнено')
        email = self.normalize_email(email)
        email = email.lower()
        phone_number = extra_fields.pop("phone_number", None)
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Администратор"),
        ("owner", "Владелец"),
        ("user", "Пользователь"),
    )
    username = None
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="user",
        verbose_name="Адрес электронной почты",
    )
    name = models.CharField(max_length=50, blank=True, verbose_name="Имя")
    email = models.EmailField(unique=True, verbose_name="Адрес электронной почты")
    phone_number = PhoneNumberField(
        unique=True, blank=True, null=True, verbose_name="Телефон"
    )
    avatar = models.ImageField(
        upload_to="avatars/", null=True, blank=True, verbose_name="Аватар"
    )
    date_joined = models.DateTimeField(
        default=timezone.now, verbose_name="Дата регистрации"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_staff = models.BooleanField(default=False, verbose_name="Статус сотрудника")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_owner(self):
        return self.role == "owner"

    @property
    def is_user(self):
        return self.role == "user"

    def __str__(self):
        return self.email


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Заведение",
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        unique_together = ("user", "place")
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"
