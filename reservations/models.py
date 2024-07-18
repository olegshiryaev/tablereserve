from datetime import date
import os
import random
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db.models.signals import pre_save
from django.db.models.signals import post_save, post_delete
from django.db.models import Count, Avg
from django.forms import ValidationError
from django.utils.text import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.urls import reverse, reverse_lazy
from PIL import Image
from django.core.validators import URLValidator
from django.db.models import Case, When, IntegerField, Value


def upload_to_city_image(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{instance.slug}.{ext}"
    return os.path.join("cities", filename)


class City(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Город")
    image = models.ImageField(
        upload_to=upload_to_city_image,
        verbose_name="Изображение",
        null=True,
        blank=True,
    )
    slug = models.SlugField(
        max_length=100, unique=True, blank=True, verbose_name="Уникальный идентификатор"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name"]


class Cuisine(models.Model):
    name = models.CharField(
        max_length=100, unique=True, verbose_name="Наименование кухни"
    )
    slug = models.SlugField(
        max_length=100, blank=True, verbose_name="Уникальный идентификатор"
    )

    class Meta:
        verbose_name = "Кухня"
        verbose_name_plural = "Кухни"

    def __str__(self):
        return self.name


class Feature(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Особенность")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Особенность"
        verbose_name_plural = "Особенности"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название тега")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="Слаг тега")

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

    class Meta:
        verbose_name = "Тип заведения"
        verbose_name_plural = "Типы заведений"
        ordering = ["name"]

    def __str__(self):
        return self.name


def upload_to_instance_directory(instance, filename):
    return os.path.join("restaurant_images", instance.place.slug, filename)


class PlaceImage(models.Model):
    place = models.ForeignKey(
        "Place",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Заведение",
    )
    image = models.ImageField(
        upload_to=upload_to_instance_directory, verbose_name="Изображение"
    )
    is_cover = models.BooleanField(default=False, verbose_name="Обложка")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return f"Изображение {self.place.name}"

    def save(self, *args, **kwargs):
        # Сначала сохраняем изображение, чтобы получить его путь
        super().save(*args, **kwargs)

        # Открываем изображение с помощью Pillow
        img = Image.open(self.image.path)

        # Проверяем размеры изображения и изменяем размер, если нужно
        max_width, max_height = 1500, 1000
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Сохраняем измененное изображение в том же месте
            img.save(self.image.path)

        # Обновляем обложку заведения, если изображение отмечено как обложка
        if self.is_cover:
            self.place.cover_image = self
            self.place.save(update_fields=["cover_image"])

    class Meta:
        verbose_name = "Изображение заведения"
        verbose_name_plural = "Изображения заведений"


@receiver(post_delete, sender=PlaceImage)
def delete_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)


class PlaceManager(models.Manager):
    def active(self):
        return (
            self.filter(is_active=True)
            .select_related("cover_image")
            .prefetch_related("cuisines", "images")
        )

    def get_popular_places(self, limit=5):
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
        PlaceType, on_delete=models.SET_NULL, null=True, verbose_name="Тип заведения"
    )
    name = models.CharField(
        max_length=100, unique=True, db_index=True, verbose_name="Название заведения"
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="places",
        verbose_name="Город заведения",
    )
    street_type = models.CharField(
        max_length=50, choices=STREET_TYPES, verbose_name="Тип улицы"
    )
    street_name = models.CharField(max_length=255, verbose_name="Название улицы")
    house_number = models.CharField(max_length=10, verbose_name="Номер дома")
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Номер телефона должен быть введен в формате: '+999999999'. Допустимо до 15 цифр.",
            )
        ],
        verbose_name="Телефон заведения",
        blank=True,
        null=True,
    )
    facebook = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Facebook",
        validators=[URLValidator],
    )
    instagram = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Instagram",
        validators=[URLValidator],
    )
    telegram = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Telegram",
        validators=[URLValidator],
    )
    whatsapp = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="WhatsApp",
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=(
                    "Номер телефона должен быть введен в формате: '+999999999'. Допустимо до 15 цифр."
                ),
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
    website = models.URLField(blank=True, verbose_name="Веб-сайт")
    cuisines = models.ManyToManyField(Cuisine, blank=True, verbose_name="Кухни")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    short_description = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Краткое описание"
    )
    average_check = models.IntegerField(
        default=0, null=True, blank=True, verbose_name="Средний чек"
    )
    features = models.ManyToManyField(
        Feature, blank=True, verbose_name="Особенности заведения"
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="places", verbose_name="Теги"
    )
    has_kids_room = models.BooleanField(
        default=False, verbose_name="Наличие детской комнаты"
    )
    capacity = models.IntegerField(default=0, verbose_name="Вместимость", blank=True)
    cover_image = models.ForeignKey(
        PlaceImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cover_for",
        verbose_name="Обложка",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Рейтинг",
    )
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name="Активное заведение"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="Уникальный идентификатор",
    )
    manager = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="managed_places",
        verbose_name="Представитель",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    objects = PlaceManager()

    class Meta:
        verbose_name = "Заведение"
        verbose_name_plural = "Заведения"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse_lazy("place_detail", kwargs={"slug": self.slug})

    def update_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            average_rating = reviews.aggregate(Avg("rating"))["rating__avg"]
            self.rating = round(average_rating, 2) if average_rating is not None else 0
        else:
            self.rating = 0
        self.save(update_fields=["rating"])

    @property
    def favorite_count(self):
        return self.favorited_by.count()

    def is_favorited_by(self, user):
        return self.favorited_by.filter(user=user).exists()

    def get_cover_image(self):
        cover_image = self.images.filter(is_cover=True).first()
        if cover_image and cover_image.image:
            return cover_image.image.url
        else:
            return settings.STATIC_URL + "images/default_place_image.jpg"

    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    @property
    def address(self):
        return (
            f"{self.get_street_type_display()} {self.street_name}, {self.house_number}"
        )

    def __str__(self):
        return self.name


@receiver(pre_save, sender=City)
@receiver(pre_save, sender=Cuisine)
@receiver(pre_save, sender=Tag)
@receiver(pre_save, sender=PlaceType)
@receiver(pre_save, sender=Place)
def pre_save_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)


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
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name="Заведение")
    day = models.CharField(
        max_length=3, choices=DAY_CHOICES, verbose_name="День недели"
    )
    open_time = models.TimeField(null=True, blank=True, verbose_name="Время открытия")
    close_time = models.TimeField(null=True, blank=True, verbose_name="Время закрытия")
    is_closed = models.BooleanField(default=False, verbose_name="Закрыто")

    def __str__(self):
        return f"{self.place.name} - {self.get_day_display()}: {self.open_time} - {self.close_time}"

    @staticmethod
    def get_sorted_schedules(place_id):
        return (
            WorkSchedule.objects.filter(place_id=place_id)
            .annotate(
                day_order=Case(
                    When(day="MON", then=Value(1)),
                    When(day="TUE", then=Value(2)),
                    When(day="WED", then=Value(3)),
                    When(day="THU", then=Value(4)),
                    When(day="FRI", then=Value(5)),
                    When(day="SAT", then=Value(6)),
                    When(day="SUN", then=Value(7)),
                    output_field=IntegerField(),
                )
            )
            .order_by("day_order")
        )

    def clean(self):
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
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="tables")
    number = models.CharField(max_length=60, verbose_name="Тип столика")
    capacity = models.IntegerField(default=4, verbose_name="Вместимость")

    def __str__(self):
        return f"Table {self.number} - {self.place.name}"

    class Meta:
        verbose_name = "Столик"
        verbose_name_plural = "Столики"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидание"),
        ("confirmed", "Подтверждено"),
        ("cancelled", "Отменено"),
    ]
    number = models.CharField(
        max_length=6, unique=True, editable=False, verbose_name="Номер заказа"
    )
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name="Заведение")
    table = models.ForeignKey(
        Table, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Столик"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Пользователь",
    )
    date = models.DateField(null=True, blank=True, verbose_name="Дата бронирования")
    time = models.TimeField(null=True, blank=True, verbose_name="Время бронирования")
    guests = models.IntegerField(
        validators=[MinValueValidator(1)], verbose_name="Количество гостей"
    )
    wishes = models.TextField(blank=True, verbose_name="Пожелания")
    customer_name = models.CharField(max_length=100, verbose_name="Имя и фамилия")
    customer_phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Номер телефона должен быть введен в формате: '+999999999'. Допустимо до 15 цифр.",
            )
        ],
        verbose_name="Телефон",
        blank=False,
        null=False,
    )
    customer_email = models.EmailField(blank=True, verbose_name="Email")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    created_at = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"{self.user} - {self.place.name} - {self.date} {self.time}"

    def get_absolute_url(self):
        return reverse("reservation-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_reservation_number()
        super().save(*args, **kwargs)

    def generate_reservation_number(self):
        while True:
            number = "".join([str(random.randint(0, 9)) for _ in range(6)])
            if not Reservation.objects.filter(number=number).exists():
                return number

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ["-date", "-time"]


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
    place = models.ForeignKey("Place", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")
    is_spam = models.BooleanField(default=False, verbose_name="Спам")
    is_inappropriate = models.BooleanField(default=False, verbose_name="Неуместный")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.user.username} for {self.place.name}"


@receiver(post_save, sender=Review)
def update_place_rating(sender, instance, created, **kwargs):
    instance.place.update_rating()


@receiver(post_delete, sender=Review)
def recalculate_rating_on_delete(sender, instance, **kwargs):
    instance.place.update_rating()


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="review_images/", verbose_name="Изображение")

    def __str__(self):
        return f"Image for review by {self.review.user.username}"


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
