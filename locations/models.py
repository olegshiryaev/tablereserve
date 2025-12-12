import os
from django.db import models
from django.utils import timezone
from pytils.translit import slugify

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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)