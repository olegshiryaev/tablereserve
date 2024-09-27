from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.templatetags.static import static
from django.core.files.storage import default_storage
from reservations.models import City, Place
from users.utils import get_avatar_upload_path


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Поле "Электронная почта" должно быть заполнено')
        email = self.normalize_email(email)
        email = email.lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        # Генерация имени пользователя в формате User-id
        user.username = f"User-{user.id}"
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
    """
    Модель пользователя
    """

    ROLE_CHOICES = (
        ("admin", "Администратор"),
        ("owner", "Владелец"),
        ("user", "Пользователь"),
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Имя пользователя",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="user",
        verbose_name="Роль",
    )
    email = models.EmailField(unique=True, verbose_name="Адрес электронной почты")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_staff = models.BooleanField(default=False, verbose_name="Статус сотрудника")
    last_activity = models.DateTimeField(
        null=True, blank=True, verbose_name="Последняя активность"
    )
    password_sent = models.BooleanField(default=False, verbose_name="Пароль отправлен")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]

    def __str__(self):
        return self.email

    def has_role(self, role):
        return self.role == role

    @property
    def is_admin(self):
        return self.has_role("admin")

    @property
    def is_owner(self):
        return self.has_role("owner")

    @property
    def is_user(self):
        return self.has_role("user")


User = get_user_model()


class Profile(models.Model):
    GENDER_CHOICES = (
        ("male", "Мужской"),
        ("female", "Женский"),
        ("other", "Не указано"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=150, blank=True, verbose_name="Имя и фамилия")
    phone_number = PhoneNumberField(
        unique=True,
        blank=True,
        null=True,
        verbose_name="Телефон",
        help_text="Введите номер телефона",
    )
    avatar = models.ImageField(
        upload_to=get_avatar_upload_path,
        blank=True,
        verbose_name="Аватар",
        help_text="Не больше 5 Мб, форматы: jpg, jpeg, png",
        validators=[FileExtensionValidator(allowed_extensions=("png", "jpg", "jpeg"))],
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="500 символов",
        verbose_name="О себе",
    )
    birth_date = models.DateField(null=True, blank=True, verbose_name="День рождения")
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default="other",
        verbose_name="Ваш пол",
    )
    city = models.ForeignKey(
        City,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Город",
        help_text="Выберите город из списка",
    )
    date_joined = models.DateTimeField(
        default=timezone.now, verbose_name="Дата регистрации"
    )
    email_notifications = models.BooleanField(
        default=True,
        verbose_name="Получать уведомления по электронной почте",
        help_text="Включите этот флажок, чтобы получать уведомления на электронную почту.",
    )

    class Meta:
        ordering = ("user",)
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        """
        Возвращает отображаемое имя:
        1. Если в профиле есть имя, возвращает его.
        2. Иначе возвращает username пользователя.
        3. Если username отсутствует, возвращает email.
        """
        return self.name or self.user.username or self.user.email

    def save(self, *args, **kwargs):
        # Удаление предыдущего аватара, если был загружен новый
        if self.pk:
            old_instance = Profile.objects.get(pk=self.pk)
            if old_instance.avatar and old_instance.avatar != self.avatar:
                if default_storage.exists(old_instance.avatar.path):
                    old_instance.avatar.delete(save=False)
        super().save(*args, **kwargs)

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return static("images/avatars/default_profile.png")

    def get_absolute_url(self):
        """
        Ссылка на профиль
        """
        return reverse("users:profile", kwargs={"id": self.user.id})


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()


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
