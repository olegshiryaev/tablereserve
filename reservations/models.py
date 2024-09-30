from datetime import date, datetime, timedelta
from django.utils.safestring import mark_safe
import os
from PIL import Image, ImageOps
import random
from django.db import models
from django.core.validators import (
    RegexValidator,
    EmailValidator,
    MinValueValidator,
    MaxValueValidator,
)
from django.db.models.signals import pre_save
from django.db.models.signals import post_save, post_delete
from django.db.models import Count, Avg
from django.forms import ValidationError
from pytils.translit import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.urls import reverse, reverse_lazy
from PIL import Image
from django.core.validators import URLValidator
from django.db.models import Case, When, IntegerField, Value
from tempfile import NamedTemporaryFile
from ckeditor.fields import RichTextField
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMessage
from django.db import transaction
from PIL import Image as PILImage
from io import BytesIO
from django.core.files.base import ContentFile


def upload_to_city_image(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{instance.slug}.{ext}"
    return os.path.join("city_images", filename)


class City(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Город")
    image = models.ImageField(
        upload_to=upload_to_city_image,
        blank=True,
        null=True,
        default="images/city_images/default.jpg",
        verbose_name="Изображение",
    )
    description = models.TextField(blank=True, verbose_name="Описание города")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Широта"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Долгота"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name="Уникальный идентификатор",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name"]


class Cuisine(models.Model):
    name = models.CharField(
        max_length=100, unique=True, verbose_name="Наименование кухни", db_index=True
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание кухни")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name="Уникальный идентификатор",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Кухня"
        verbose_name_plural = "Кухни"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Feature(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Особенность")
    slug = models.SlugField(
        max_length=100, blank=True, verbose_name="Уникальный идентификатор"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Особенность"
        verbose_name_plural = "Особенности"
        ordering = ["name"]


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название тега")
    slug = models.SlugField(
        max_length=100, unique=True, verbose_name="Уникальный идентификатор"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlaceType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Тип заведения")
    slug = models.SlugField(
        max_length=50, unique=True, blank=True, verbose_name="Уникальный идентификатор"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Тип заведения"
        verbose_name_plural = "Типы заведений"
        ordering = ["name"]

    def __str__(self):
        return self.name


def upload_to_instance_directory(instance, filename):
    return os.path.join("restaurant_images", instance.place.slug, filename)


def upload_logo_to(instance, filename):
    return os.path.join("place_logos", instance.slug, filename)


class PlaceImage(models.Model):
    place = models.ForeignKey(
        "Place",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Заведение",
    )
    hall = models.ForeignKey(
        "Hall",
        on_delete=models.SET_NULL,
        related_name="images",
        verbose_name="Зона",
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to=upload_to_instance_directory,
        verbose_name="Изображение",
        blank=True,
        null=True,
    )
    video_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на видео")
    embed_code = models.TextField(
        blank=True, null=True, verbose_name="Код для встраивания видео"
    )
    is_cover = models.BooleanField(default=False, verbose_name="Обложка")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return f"Медиа {self.place.name}"

    def clean(self):
        if self.image:
            img = Image.open(self.image)
            min_width, min_height = 1200, 800
            if img.width < min_width or img.height < min_height:
                raise ValidationError(
                    f"Размер изображения должен быть не менее {min_width}x{min_height} пикселей."
                )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            try:
                img = Image.open(self.image.path)
                max_width, max_height = 1200, 800

                # Изменение размера изображения, если оно превышает заданные параметры
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # Сжатие изображения и учёт ориентации EXIF
                img = ImageOps.exif_transpose(img)
                img.save(self.image.path, quality=85, optimize=True)
            except Exception as e:
                raise ValidationError(f"Ошибка при обработке изображения: {e}")

        # Устанавливаем только одно изображение обложки
        if self.is_cover:
            self.place.images.exclude(id=self.id).update(is_cover=False)

    class Meta:
        verbose_name = "Медиа заведения"
        verbose_name_plural = "Медиа заведений"

    def get_media_display(self):
        if self.embed_code:
            return mark_safe(self.embed_code)
        elif self.video_url:
            return mark_safe(
                f'<iframe width="840" height="560" src="{self.video_url}" frameborder="0" allowfullscreen></iframe>'
            )
        elif self.image:
            return mark_safe(f'<img src="{self.image.url}" alt="{self.place.name}" />')
        return "Нет медиа"


@receiver(post_delete, sender=PlaceImage)
def delete_image_file(sender, instance, **kwargs):
    """Удаляем файл изображения при удалении модели."""
    if instance.image and os.path.exists(instance.image.path):
        os.remove(instance.image.path)


class PlaceManager(models.Manager):
    def active(self):
        return (
            self.filter(is_active=True)
            .select_related("type", "city")
            .prefetch_related("cuisines", "images")
        )

    def get_popular_places(self, limit=8):
        return (
            self.filter(is_active=True)
            .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
            .order_by("-avg_rating", "-review_count")[:limit]
        )


class Place(models.Model):
    STREET_TYPES = [
        ("улица", "ул."),
        ("проспект", "пр-кт"),
        ("переулок", "пер."),
        ("набережная", "наб."),
        ("бульвар", "б-р"),
        ("шоссе", "ш."),
        ("площадь", "пл."),
        ("аллея", "ал."),
        ("линия", "лн."),
        ("проезд", "пр-д"),
    ]
    type = models.ForeignKey(
        PlaceType,
        on_delete=models.SET_NULL,
        related_name="places",
        blank=False,
        null=True,
        verbose_name="Тип",
        db_index=True,
    )
    name = models.CharField(
        max_length=100, unique=True, db_index=True, verbose_name="Название"
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="places",
        verbose_name="Город",
        db_index=True,
    )
    # Адрес заведения: тип улицы, название улицы, номер дома и этаж
    street_type = models.CharField(
        max_length=50,
        choices=STREET_TYPES,
        blank=True,
        null=True,
        verbose_name="Тип улицы",
        default="",
    )
    street_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Название улицы"
    )
    house_number = models.CharField(
        max_length=5, blank=True, null=True, verbose_name="Номер дома"
    )
    floor = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        verbose_name="Этаж",
        help_text="Укажите этаж, если заведение находится не на первом этаже",
    )
    # Поля для контактной информации: телефон, соцсети, эл. почта, вебсайт
    phone = models.CharField(
        max_length=12,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Номер телефона должен быть введен в формате: '+79999999999'. Допустимо до 12 цифр.",
            )
        ],
        verbose_name="Телефон",
    )
    facebook = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        validators=[URLValidator],
    )
    instagram = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        validators=[URLValidator],
    )
    telegram = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        validators=[URLValidator],
    )
    whatsapp = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=(
                    "Номер телефона должен быть введен в формате: '+79999999999'. Допустимо до 12 цифр."
                ),
            )
        ],
    )
    viber = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Номер телефона должен быть введен в формате: '+79999999999'. Допустимо до 12 цифр.",
            )
        ],
    )
    vkontakte = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ВКонтакте",
        validators=[URLValidator],
    )
    odnoklassniki = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Одноклассники",
        validators=[URLValidator],
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Эл. почта",
        validators=[EmailValidator],
    )
    website = models.URLField(blank=True, verbose_name="Веб-сайт")
    # Прочие поля: описание, рейтинг, особенности, вместимость и т.д.
    cuisines = models.ManyToManyField(
        Cuisine, related_name="places", blank=True, verbose_name="Кухни"
    )
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    short_description = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Краткое описание"
    )
    average_check = models.IntegerField(
        default=0, null=True, blank=True, verbose_name="Средний чек"
    )
    features = models.ManyToManyField(
        Feature,
        through="PlaceFeature",
        related_name="places",
        blank=True,
        verbose_name="Особенности",
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="places", verbose_name="Теги"
    )
    capacity = models.IntegerField(default=0, verbose_name="Вместимость", blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Рейтинг",
        db_index=True,
    )
    # Слаг и лого
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="Уникальный идентификатор",
    )
    logo = models.ImageField(
        upload_to=upload_logo_to, verbose_name="Логотип", null=True, blank=True
    )
    # Поле manager для представителя заведения
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Представитель",
    )
    # Состояние заведения (активность, популярность и т.д.)
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name="Активное"
    )
    is_popular = models.BooleanField(default=False, verbose_name="Популярное")
    is_featured = models.BooleanField(default=False, verbose_name="Рекомендуемое")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    objects = PlaceManager()

    class Meta:
        verbose_name = "Заведение"
        verbose_name_plural = "Заведения"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        """
        Переопределение метода save:
        1. Генерация slug на основе имени заведения, если оно не задано.
        2. Обработка изображения логотипа: ресайз до 100x100 для оптимизации.
        """
        # Генерация slug, если его нет или изменено название
        if not self.slug or self.slug != slugify(self.name):
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

        # Обработка логотипа: изменение размера изображения до 100x100
        if self.logo:
            img = Image.open(self.logo.path)
            if img.width > 100 or img.height > 100:
                # Ресайз изображения для оптимизации
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                img.save(self.logo.path)

    def get_absolute_url(self):
        return reverse(
            "place_detail",
            kwargs={"city_slug": self.city.slug, "place_slug": self.slug},
        )

    def update_rating(self):
        reviews = (
            self.reviews.select_related("user")
            .filter(status="approved")
            .annotate(avg_rating=Avg("rating"))
        )
        if reviews.exists():
            average_rating = reviews.aggregate(Avg("rating"))["rating__avg"]
            self.rating = round(average_rating, 2) if average_rating is not None else 0
        else:
            self.rating = 0
        self.save(update_fields=["rating"])

    def get_cover_image(self):
        cover_image = self.images.filter(is_cover=True).first()
        if cover_image:
            return cover_image.image.url
        return None

    def get_similar_places(self):
        return Place.objects.filter(type=self.type, city=self.city).exclude(id=self.id)[
            :4
        ]

    def get_place_features(self):
        return PlaceFeature.objects.filter(place=self).select_related("feature")

    @property
    def favorite_count(self):
        return self.favorited_by.count()

    def is_favorited_by(self, user):
        return self.favorited_by.filter(user=user).exists()

    def approved_reviews(self):
        return self.reviews.filter(status="approved")

    def get_status(self):
        current_time = datetime.now()
        work_schedules = self.work_schedule.all()  # Заранее загружаем расписание
        if self.is_open_for_booking(current_time, work_schedules):
            closing_time = self.get_working_hours(
                current_time.strftime("%a").upper(), work_schedules
            )
            if closing_time:
                return {
                    "status": "open",
                    "message": f"Открыто до {closing_time[-1][1].strftime('%H:%M')}",
                }
        else:
            opening_time = self.get_working_hours(
                (current_time + timedelta(days=1)).strftime("%a").upper(),
                work_schedules,
            )
            if opening_time:
                return {
                    "status": "closed",
                    "message": f"Закрыто до {opening_time[0][0].strftime('%H:%M')}",
                }
        return {"status": "closed", "message": "Закрыто"}

    def get_working_hours(self, day=None, work_schedules=None):
        """
        Возвращает время работы заведения на указанный день недели (или сегодня).
        Если заведению характерны перерывы в течение дня, возвращает все интервалы.
        """
        if day is None:
            day = datetime.now().strftime("%a").upper()

        # Используем предварительно загруженные расписания, если они переданы
        schedules = (
            work_schedules if work_schedules is not None else self.work_schedule.all()
        )
        day_schedules = schedules.filter(day=day, is_closed=False)

        if day_schedules.exists():
            return [
                (schedule.open_time, schedule.close_time) for schedule in day_schedules
            ]
        return []

    def is_open_for_booking(self, booking_time, work_schedules=None):
        """Проверяет, открыто ли заведение для бронирования на указанное время."""
        booking_day = booking_time.strftime("%a").upper()
        working_hours = self.get_working_hours(booking_day, work_schedules)

        for open_time, close_time in working_hours:
            if open_time < close_time:
                if open_time <= booking_time.time() <= close_time:
                    return True
            else:
                # Пересечение полуночи
                if (
                    booking_time.time() >= open_time
                    or booking_time.time() <= close_time
                ):
                    return True

        return False  # Заведение закрыто

    def get_available_time_slots(self, date):
        """Возвращает доступные временные слоты для бронирования на указанную дату."""
        day = date.strftime("%a").upper()
        schedules = self.work_schedule.filter(day=day, is_closed=False)
        # Получаем настройки бронирования для заведения
        booking_settings = self.booking_settings
        # Получаем интервал из BookingSettings
        interval = timedelta(minutes=booking_settings.booking_interval)
        slots = []

        for schedule in schedules:
            current_time = datetime.combine(date, schedule.open_time)
            end_time = datetime.combine(date, schedule.close_time)
            if schedule.open_time > schedule.close_time:
                end_time += timedelta(days=1)

            while current_time < end_time:
                slots.append(current_time.time())
                current_time += interval

        return slots

    @property
    def review_count(self):
        return self.reviews.filter(status="approved").count()

    @property
    def address(self):
        if self.street_type and self.street_name and self.house_number:
            base_address = f"{self.get_street_type_display()} {self.street_name}, {self.house_number}"
            if self.floor:
                return f"{base_address}, {self.floor} этаж"
            return base_address
        return None

    def __str__(self):
        return self.name


@receiver(post_save, sender=Place)
def create_default_work_schedule(sender, instance, created, **kwargs):
    if created:
        days = WorkSchedule.DAY_CHOICES
        for day in days:
            WorkSchedule.objects.create(
                place=instance,
                day=day[0],
                is_closed=True,
            )


@receiver(post_save, sender=Place)
def create_booking_settings(sender, instance, created, **kwargs):
    if created:
        # Создаем настройки бронирования
        booking_settings = BookingSettings.objects.create(place=instance)
        # Устанавливаем email менеджера в notification_email
        if instance.manager:
            booking_settings.notification_email = instance.manager.email
            booking_settings.save(update_fields=["notification_email"])


@receiver(pre_save, sender=City)
@receiver(pre_save, sender=Cuisine)
@receiver(pre_save, sender=Feature)
@receiver(pre_save, sender=Tag)
@receiver(pre_save, sender=PlaceType)
@receiver(pre_save, sender=Place)
def pre_save_slug(sender, instance, *args, **kwargs):
    if isinstance(instance, City):
        # Для модели City: если слаг не задан, генерируем его
        if not instance.slug:
            instance.slug = slugify(instance.name)
    else:
        # Для всех остальных моделей: если слаг не задан или изменен, генерируем новый
        if not instance.slug or instance.slug != slugify(instance.name):
            instance.slug = slugify(instance.name)


class BookingSettings(models.Model):
    place = models.OneToOneField(
        Place,
        on_delete=models.CASCADE,
        related_name="booking_settings",
        verbose_name="Заведение",
    )
    accepts_bookings = models.BooleanField(
        default=False,
        verbose_name="Доступно для бронирования",
        help_text="Отметьте, если хотите разрешить бронирования для этого заведения",
    )
    booking_interval = models.PositiveIntegerField(
        default=30,
        verbose_name="Интервал между бронированиями (минуты)",
        help_text="Укажите интервал в минутах. Не менее 30 минут",
        validators=[MinValueValidator(30)],
    )
    default_guest_count = models.PositiveIntegerField(
        default=2, verbose_name="Количество гостей по умолчанию"
    )
    allow_table_selection = models.BooleanField(
        default=False,
        verbose_name="Выбор столика на форме бронирования",
        help_text="Столики нужно добавить в разделе «Столики»",
    )
    notification_email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Email для уведомлений о бронированиях",
        help_text="Оставьте пустым, чтобы не получать уведомления по электронной почте",
    )

    class Meta:
        verbose_name = "Настройки бронирования"
        verbose_name_plural = "Настройки бронирования"

    def __str__(self):
        return f"Настройки бронирования для {self.place.name}"


class Hall(models.Model):
    HALL_KIND_CHOICES = [
        ("real", "Реальная"),
        ("virtual", "Виртуальная"),
    ]

    HALL_TYPE_CHOICES = [
        ("outdoor", "На улице"),
        ("panoramic_windows", "Панорамные окна"),
        ("terrace", "Терраса"),
        ("main_hall", "Основной зал"),
        ("small_hall", "Малый зал"),
        ("vip_hall", "ВИП зал"),
        ("booth", "Кабинка"),
    ]

    name = models.CharField(max_length=100, verbose_name="Название зоны")
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="halls",
        verbose_name="Заведение",
    )
    kind = models.CharField(
        max_length=10,
        choices=HALL_KIND_CHOICES,
        default="real",
        verbose_name="Вид зоны",
    )
    hall_type = models.CharField(
        max_length=20, choices=HALL_TYPE_CHOICES, verbose_name="Тип зоны"
    )
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    number_of_seats = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Количество посадочных мест"
    )
    area = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Площадь (м²)",
    )

    class Meta:
        verbose_name = "Зона"
        verbose_name_plural = "Зоны"
        unique_together = (
            ("place", "name"),
        )  # Сектора должны быть уникальны в рамках одного заведения

    def __str__(self):
        return (
            f"{self.name} ({self.get_kind_display()} - {self.get_hall_type_display()})"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class WorkSchedule(models.Model):
    DAY_CHOICES = (
        ("MON", "Понедельник"),
        ("TUE", "Вторник"),
        ("WED", "Среда"),
        ("THU", "Четверг"),
        ("FRI", "Пятница"),
        ("SAT", "Суббота"),
        ("SUN", "Воскресенье"),
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="work_schedule",
        verbose_name="Заведение",
    )
    day = models.CharField(
        max_length=3, choices=DAY_CHOICES, verbose_name="День недели"
    )
    open_time = models.TimeField(null=True, blank=True, verbose_name="Время открытия")
    close_time = models.TimeField(null=True, blank=True, verbose_name="Время закрытия")
    is_closed = models.BooleanField(default=False, verbose_name="Выходной")

    def __str__(self):
        return f"{self.place.name} - {self.get_day_display()}: {'Выходной' if self.is_closed else f'{self.open_time} - {self.close_time}'}"

    @staticmethod
    def get_day_order_annotation():
        return Case(
            When(day="MON", then=Value(1)),
            When(day="TUE", then=Value(2)),
            When(day="WED", then=Value(3)),
            When(day="THU", then=Value(4)),
            When(day="FRI", then=Value(5)),
            When(day="SAT", then=Value(6)),
            When(day="SUN", then=Value(7)),
            output_field=IntegerField(),
        )

    @staticmethod
    def get_sorted_schedules(place_id):
        """Возвращает отсортированное расписание для указанного заведения."""
        return (
            WorkSchedule.objects.filter(place_id=place_id)
            .annotate(day_order=WorkSchedule.get_day_order_annotation())
            .order_by("day_order")
        )

    def clean(self):
        """Проверяет корректность заполненных полей для модели WorkSchedule."""
        if self.is_closed:
            self.open_time = None
            self.close_time = None
        else:
            if not self.open_time or not self.close_time:
                raise ValidationError(
                    "Введите время открытия и закрытия или отметьте, что заведение в этот день закрыто."
                )

    class Meta:
        verbose_name = "Время работы"
        verbose_name_plural = "Время работы"
        unique_together = ("place", "day")


class Table(models.Model):
    BOOKING_PAYMENT_CHOICES = [
        ("advance", "Аванс"),
        ("no_advance", "Без аванса"),
    ]
    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, related_name="tables", verbose_name="Зал"
    )
    name = models.CharField(
        max_length=100, verbose_name="Наименование столика", blank=True
    )
    seats = models.PositiveIntegerField(default=4, verbose_name="Количество мест")
    photo = models.ImageField(
        upload_to="table_photos/", verbose_name="Фото столика", null=True, blank=True
    )
    quantity = models.PositiveIntegerField(
        default=1, verbose_name="Количество столиков данного вида"
    )
    min_booking_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        default=2,
        verbose_name="Минимальное количество мест для бронирования",
    )  # Значение по умолчанию: 2 места
    min_booking_period = models.DurationField(
        default=timedelta(minutes=30), verbose_name="Минимальный период бронирования"
    )
    max_booking_period = models.DurationField(
        default=timedelta(hours=2), verbose_name="Максимальный период бронирования"
    )
    booking_payment = models.CharField(
        max_length=10,
        choices=BOOKING_PAYMENT_CHOICES,
        default="no_advance",
        verbose_name="Оплата бронирования",
    )
    booking_interval = models.DurationField(
        default=timedelta(minutes=30), verbose_name="Период между бронированиями"
    )  # Значение по умолчанию: 30 минут

    class Meta:
        verbose_name = "Столик"
        verbose_name_plural = "Столики"

    def save(self, *args, **kwargs):
        # Автоматическая генерация названия столика
        if not self.name:
            self.name = f"Столик - {self.hall.name} на {self.seats}-х"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.hall.name}, {self.seats} мест)"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает подтверждения"),
        ("confirmed", "Подтвержден рестораном"),
        ("cancelled_by_restaurant", "Отменен рестораном"),
        ("cancelled_by_customer", "Отменен клиентом"),
    ]
    number = models.PositiveIntegerField(
        unique=True, editable=False, verbose_name="Номер заказа"
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="Заведение",
    )
    table = models.ForeignKey(
        Table,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reservations",
        verbose_name="Столик",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
        blank=True,
        null=True,
        verbose_name="Пользователь",
    )
    date = models.DateField(null=True, blank=True, verbose_name="Дата бронирования")
    time = models.TimeField(null=True, blank=True, verbose_name="Время бронирования")
    guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="Количество гостей"
    )
    wishes = models.TextField(blank=True, verbose_name="Пожелания")
    customer_name = models.CharField(max_length=100, verbose_name="Имя и фамилия")
    customer_phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,12}$",
                message="Номер телефона должен быть введен в формате: '+79999999999'",
            )
        ],
        verbose_name="Телефон",
        blank=False,
        null=False,
    )
    customer_email = models.EmailField(blank=True, verbose_name="Email")
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    created_at = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"{self.user or self.customer_name} - {self.place.name} - {self.date} {self.time}"

    def get_absolute_url(self):
        return reverse("users:reservation-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_reservation_number()
        super().save(*args, **kwargs)

    def generate_reservation_number(self):
        with transaction.atomic():
            max_number = (
                Reservation.objects.select_for_update().aggregate(models.Max("number"))[
                    "number__max"
                ]
                or 0
            )
            return max_number + 1

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ["-date", "-time"]


class PlaceFeature(models.Model):
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="place_features"
    )
    feature = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="place_features"
    )
    description = models.TextField(
        blank=True, null=True, verbose_name="Описание особенности"
    )
    display_on_card = models.BooleanField(
        default=False, verbose_name="Отображать на карточке"
    )

    class Meta:
        unique_together = (
            "place",
            "feature",
        )  # Это ограничивает повторение одной и той же особенности для одного заведения
        verbose_name = "Особенность заведения"
        verbose_name_plural = "Особенности заведения"

    def __str__(self):
        return f"{self.place.name} - {self.feature.name}: {self.description}"


class Menu(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="menus")
    name = models.CharField(max_length=100, verbose_name="Название меню")
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return f"{self.name} - {self.place.name}"

    class Meta:
        verbose_name = "Меню"
        verbose_name_plural = "Меню"


class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=100, verbose_name="Название блюда")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(
        upload_to="menu_images/", null=True, blank=True, verbose_name="Изображение"
    )
    is_available = models.BooleanField(default=True, verbose_name="Доступно")

    def __str__(self):
        return f"{self.name} - {self.menu.name}"

    class Meta:
        verbose_name = "Пункт меню"
        verbose_name_plural = "Пункты меню"


class Review(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает модерации"),
        ("approved", "Одобрен"),
        ("spam", "Спам"),
        ("inappropriate", "Неуместный"),
    ]
    place = models.ForeignKey("Place", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    text = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="approved", verbose_name="Статус"
    )

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        unique_together = ["user", "place"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.user.username} for {self.place.name}"


@receiver(post_save, sender=Review)
def update_place_rating(sender, instance, created, **kwargs):
    instance.place.update_rating()


@receiver(post_delete, sender=Review)
def recalculate_rating_on_delete(sender, instance, **kwargs):
    instance.place.update_rating()


def save_resized_image(self, image, size=(800, 800)):
    img = PILImage.open(image)
    img.thumbnail(size, PILImage.ANTIALIAS)
    img_io = BytesIO()
    img.save(img_io, format="JPEG", quality=85)
    return ContentFile(img_io.getvalue(), name=image.name)


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="review_images/", verbose_name="Изображение")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def save(self, *args, **kwargs):
        if self.image:
            self.image = save_resized_image(self.image)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for review by {self.review.user.username}"


class ReviewResponse(models.Model):
    review = models.OneToOneField(
        Review, on_delete=models.CASCADE, related_name="response"
    )
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_responses",
    )
    text = models.TextField(verbose_name="Текст ответа")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата ответа")
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Дата обновления ответа"
    )

    class Meta:
        verbose_name = "Ответ на отзыв"
        verbose_name_plural = "Ответы на отзывы"
        ordering = ["created_at"]

    def __str__(self):
        return f"Ответ на отзыв {self.review.id} для {self.place.name} от {self.user.username}"


class Event(models.Model):
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="events", verbose_name="Заведение"
    )
    name = models.CharField(max_length=100, verbose_name="Название события")
    description = models.TextField(blank=True, verbose_name="Описание")
    date = models.DateField(verbose_name="Дата")
    start_time = models.TimeField(verbose_name="Время начала")
    end_time = models.TimeField(verbose_name="Время окончания")
    image = models.ImageField(
        upload_to="events/", null=True, blank=True, verbose_name="Изображение"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активное мероприятие")

    def __str__(self):
        return f"{self.name} - {self.place.name}"

    def get_upcoming_events(self, limit=5):
        today = date.today()
        return Event.objects.filter(
            place=self.place, date__gte=today, is_active=True
        ).order_by("date", "start_time")[:limit]

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"


class Discount(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="discounts",
        verbose_name="Заведение",
    )
    title = models.CharField(max_length=100, verbose_name="Название акции")
    description = models.TextField(blank=True, verbose_name="Описание")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="Процент скидки"
    )
    image = models.ImageField(
        upload_to="discounts/", null=True, blank=True, verbose_name="Изображение"
    )

    def __str__(self):
        return f"{self.title} - {self.place.name}"

    def get_active_discounts(self, limit=5):
        today = date.today()
        return Discount.objects.filter(
            place=self.place, start_date__lte=today, end_date__gte=today
        ).order_by("end_date")[:limit]

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"


class PlaceUpdateRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Ожидает рассмотрения"),
        ("approved", "Одобрено"),
        ("rejected", "Отклонено"),
    )
    STREET_TYPES = [
        ("улица", "ул."),
        ("проспект", "пр-кт"),
        ("переулок", "пер."),
        ("набережная", "наб."),
        ("бульвар", "б-р"),
        ("шоссе", "ш."),
        ("площадь", "пл."),
        ("аллея", "ал."),
        ("линия", "лн."),
        ("проезд", "пр-д"),
    ]
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="update_requests"
    )
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    updated_type = models.ForeignKey(
        PlaceType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Тип заведения",
    )
    updated_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Название заведения"
    )
    updated_street_type = models.CharField(
        max_length=50,
        choices=STREET_TYPES,
        blank=True,
        null=True,
        verbose_name="Тип улицы",
    )
    updated_street_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Название улицы"
    )
    updated_house_number = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Номер дома"
    )
    updated_phone = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="Телефон заведения"
    )
    updated_facebook = models.URLField(
        max_length=255, blank=True, null=True, verbose_name="Facebook"
    )
    updated_instagram = models.URLField(
        max_length=255, blank=True, null=True, verbose_name="Instagram"
    )
    updated_telegram = models.URLField(
        max_length=255, blank=True, null=True, verbose_name="Telegram"
    )
    updated_whatsapp = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="WhatsApp"
    )
    updated_vkontakte = models.URLField(
        max_length=255, blank=True, null=True, verbose_name="ВКонтакте"
    )
    updated_website = models.URLField(blank=True, verbose_name="Веб-сайт")
    updated_description = models.TextField(
        blank=True, null=True, verbose_name="Описание"
    )
    updated_short_description = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Краткое описание"
    )
    updated_average_check = models.IntegerField(
        blank=True, null=True, verbose_name="Средний чек"
    )
    updated_capacity = models.IntegerField(
        blank=True, null=True, verbose_name="Вместимость"
    )
    updated_cover_image = models.ImageField(
        upload_to="place_images/", null=True, blank=True, verbose_name="Обложка"
    )
    updated_features = models.ManyToManyField(
        Feature,
        blank=True,
        related_name="update_requests",
        verbose_name="Особенности заведения",
    )
    updated_tags = models.ManyToManyField(
        Tag, blank=True, related_name="update_requests", verbose_name="Теги"
    )

    def get_updated_fields(self):
        updated_fields = {}
        if self.updated_type:
            updated_fields["Тип заведения"] = self.updated_type
        if self.updated_name:
            updated_fields["Название заведения"] = self.updated_name
        if self.updated_street_type:
            updated_fields["Тип улицы"] = self.updated_street_type
        if self.updated_street_name:
            updated_fields["Название улицы"] = self.updated_street_name
        if self.updated_house_number:
            updated_fields["Номер дома"] = self.updated_house_number
        if self.updated_phone:
            updated_fields["Телефон заведения"] = self.updated_phone
        if self.updated_facebook:
            updated_fields["Facebook"] = self.updated_facebook
        if self.updated_instagram:
            updated_fields["Instagram"] = self.updated_instagram
        if self.updated_telegram:
            updated_fields["Telegram"] = self.updated_telegram
        if self.updated_whatsapp:
            updated_fields["WhatsApp"] = self.updated_whatsapp
        if self.updated_vkontakte:
            updated_fields["ВКонтакте"] = self.updated_vkontakte
        if self.updated_website:
            updated_fields["Веб-сайт"] = self.updated_website
        if self.updated_description:
            updated_fields["Описание"] = self.updated_description
        if self.updated_short_description:
            updated_fields["Краткое описание"] = self.updated_short_description
        if self.updated_average_check is not None:
            updated_fields["Средний чек"] = self.updated_average_check
        if self.updated_capacity:
            updated_fields["Вместимость"] = self.updated_capacity
        if self.updated_cover_image:
            updated_fields["Обложка"] = self.updated_cover_image
        if self.updated_features.exists():
            updated_fields["Особенности заведения"] = self.updated_features.all()
        if self.updated_tags.exists():
            updated_fields["Теги"] = self.updated_tags.all()
        return updated_fields

    def __str__(self):
        return f"Запрос на обновление для {self.place.name}"


class Booking(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Заведение",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Пользователь",
    )
    booking_time = models.DateTimeField(verbose_name="Время бронирования")
    guests_count = models.IntegerField(verbose_name="Количество гостей")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"

    def clean(self):
        # Проверка на соответствие времени бронирования времени работы заведения
        if not self.place.is_open_for_booking(self.booking_time):
            raise ValidationError("Заведение закрыто в выбранное время.")

        # Дополнительные проверки, например, на максимальное количество гостей или наличие свободных столиков
