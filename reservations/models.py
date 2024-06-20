import os
import random
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db.models.signals import pre_save
from django.db.models.signals import post_save, post_delete
from django.db.models import Avg
from django.forms import ValidationError
from django.utils.text import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.urls import reverse


def upload_to_city_image(instance, filename):
    # Получаем расширение загружаемого файла
    ext = filename.split('.')[-1]
    # Генерируем имя файла в формате <slug города>.jpg
    filename = f"{instance.slug}.{ext}"
    # Возвращаем путь для сохранения файла
    return os.path.join('cities', filename)


class City(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Город")
    image = models.ImageField(upload_to=upload_to_city_image, verbose_name="Изображение", null=True, blank=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name="Уникальный идентификатор")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ['name']


class Cuisine(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Наименование кухни")
    slug = models.SlugField(max_length=100, blank=True, verbose_name="Уникальный идентификатор")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

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


class PlaceType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Тип заведения")
    slug = models.SlugField(max_length=50, unique=True, blank=True, verbose_name="Уникальный идентификатор")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип заведения"
        verbose_name_plural = "Типы заведений"
        ordering = ['name']


def upload_to_instance_directory(instance, filename):
    return os.path.join("restaurant_images", instance.place.slug, filename)


class PlaceImage(models.Model):
    place = models.ForeignKey('Place', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=upload_to_instance_directory, verbose_name="Изображение")
    is_cover = models.BooleanField(default=False, verbose_name="Обложка")

    def __str__(self):
        return f"Image for {self.place.name}"


class PlaceManager(models.Manager):
    def active(self):
        return self.filter(is_active=True).select_related('cover_image').prefetch_related('cuisines', 'images')


class Place(models.Model):
    type = models.ForeignKey(PlaceType, on_delete=models.SET_NULL, null=True, verbose_name="Тип заведения")
    name = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Название заведения")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='places', verbose_name="Город заведения")
    address = models.CharField(max_length=255, verbose_name="Адрес заведения")
    phone = models.CharField(max_length=15,
                             validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                                        message="Номер телефона должен быть введен в формате: '+999999999'. Допустимо до 15 цифр.")],
                             verbose_name="Телефон заведения"
                             )
    website = models.URLField(blank=True, verbose_name="Веб-сайт")
    cuisines = models.ManyToManyField(Cuisine, blank=True, verbose_name="Кухни")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    average_check = models.IntegerField(default=0, verbose_name="Средний чек")
    features = models.ManyToManyField(Feature, blank=True, verbose_name="Особенности заведения")
    has_kids_room = models.BooleanField(default=False, verbose_name="Наличие детской комнаты")
    capacity = models.IntegerField(default=0, verbose_name="Вместимость")
    cover_image = models.ForeignKey(PlaceImage, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='cover_for', verbose_name="Обложка")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0,
                                 validators=[MinValueValidator(0), MaxValueValidator(5)], verbose_name="Рейтинг")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Активное заведение")
    slug = models.SlugField(max_length=100, unique=True, blank=True, db_index=True,
                            verbose_name="Уникальный идентификатор")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                              related_name='establishments', verbose_name="Владелец")

    objects = PlaceManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def update_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
            self.rating = round(average_rating, 2) if average_rating is not None else 0
        else:
            self.rating = 0
        self.save(update_fields=['rating'])

    def get_cover_image(self):
        return self.images.filter(is_cover=True).first()

    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)

    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Заведение"
        verbose_name_plural = "Заведения"
        ordering = ['name']


class WorkSchedule(models.Model):
    WEEKDAYS = (
        ('MON', 'Понедельник'),
        ('TUE', 'Вторник'),
        ('WED', 'Среда'),
        ('THU', 'Четверг'),
        ('FRI', 'Пятница'),
        ('SAT', 'Суббота'),
        ('SUN', 'Воскресенье'),
    )
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name="Заведение")
    weekday = models.CharField(max_length=3, choices=WEEKDAYS, verbose_name="День недели")
    opening_time = models.TimeField(verbose_name="Время открытия")
    closing_time = models.TimeField(verbose_name="Время закрытия")
    is_closed = models.BooleanField(default=False, verbose_name="Закрыто")

    def clean(self):
        if self.opening_time >= self.closing_time:
            raise ValidationError('Время открытия должно быть раньше времени закрытия.')

    def __str__(self):
        return f"{self.place.name} - {self.get_weekday_display()}: {self.opening_time} - {self.closing_time}"

    class Meta:
        verbose_name = "Время работы"
        verbose_name_plural = "Время работы"


class Table(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='tables')
    number = models.CharField(max_length=60, verbose_name="Тип столика")
    capacity = models.IntegerField(default=4, verbose_name="Вместимость")

    def __str__(self):
        return f"Table {self.number} - {self.place.name}"

    class Meta:
        verbose_name = "Столик"
        verbose_name_plural = "Столики"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
    ]
    number = models.CharField(max_length=6, unique=True, editable=False, verbose_name="Номер заказа")
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name="Заведение")
    table = models.ForeignKey(Table, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Столик")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                             verbose_name="Пользователь")
    date = models.DateField(null=True, blank=True, verbose_name="Дата бронирования")
    time = models.TimeField(null=True, blank=True, verbose_name="Время бронирования")
    guests = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Количество гостей")
    wishes = models.TextField(blank=True, verbose_name="Пожелания")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="Фамилия")
    phone = models.CharField(max_length=15,
                             validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                                        message="Номер телефона должен быть введен в формате: '+999999999'. Допустимо до 15 цифр.")],
                             verbose_name="Телефон", blank=False, null=False
                             )
    email = models.EmailField(blank=True, verbose_name="Email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"{self.user} - {self.place.name} - {self.date} {self.time}"

    def get_absolute_url(self):
        return reverse('reservation-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_reservation_number()
        super().save(*args, **kwargs)

    def generate_reservation_number(self):
        while True:
            number = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            if not Reservation.objects.filter(number=number).exists():
                return number

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ['-date', '-time']  # Порядок отображения по умолчанию


class Menu(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='menus')
    name = models.CharField(max_length=100, verbose_name="Название меню")
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return f"{self.name} - {self.place.name}"

    class Meta:
        verbose_name = "Меню"
        verbose_name_plural = "Меню"


class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100, verbose_name="Название блюда")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(upload_to='menu_images/', null=True, blank=True, verbose_name="Изображение")
    is_available = models.BooleanField(default=True, verbose_name="Доступно")

    def __str__(self):
        return f"{self.name} - {self.menu.name}"

    class Meta:
        verbose_name = "Пункт меню"
        verbose_name_plural = "Пункты меню"


class Review(models.Model):
    place = models.ForeignKey('Place', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")
    is_spam = models.BooleanField(default=False, verbose_name="Спам")
    is_inappropriate = models.BooleanField(default=False, verbose_name="Неуместный")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.place.name}"


@receiver(post_save, sender=Review)
def update_place_rating(sender, instance, created, **kwargs):
    instance.place.update_rating()


@receiver(post_delete, sender=Review)
def recalculate_rating_on_delete(sender, instance, **kwargs):
    instance.place.update_rating()


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='review_images/', verbose_name="Изображение")

    def __str__(self):
        return f"Image for review by {self.review.user.username}"


class Event(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=100, verbose_name="Название мероприятия")
    description = models.TextField(blank=True, verbose_name="Описание")
    date = models.DateField(verbose_name="Дата")
    start_time = models.TimeField(verbose_name="Время начала")
    end_time = models.TimeField(verbose_name="Время окончания")
    is_active = models.BooleanField(default=True, verbose_name="Активное мероприятие")

    def __str__(self):
        return f"{self.name} - {self.place.name}"

    class Meta:
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"


class Discount(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='discounts')
    title = models.CharField(max_length=100, verbose_name="Название акции")
    description = models.TextField(blank=True, verbose_name="Описание")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Процент скидки")

    def __str__(self):
        return f"{self.title} - {self.place.name}"

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
