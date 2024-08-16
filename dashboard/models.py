from django.db import models
from django.utils import timezone

from reservations.models import City


class PlaceRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидание"),
        ("approved", "Одобрено"),
        ("rejected", "Отклонено"),
    ]

    owner_name = models.CharField(max_length=50, verbose_name="Имя владельца")
    owner_email = models.EmailField(verbose_name="Email владельца")
    name = models.CharField(max_length=255, verbose_name="Название заведения")
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name="Дата создания"
    )

    def __str__(self):
        return self.name
