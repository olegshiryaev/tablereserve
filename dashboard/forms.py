# forms.py
from django import forms
from dashboard.models import PlaceRequest
from reservations.models import (
    City,
    Cuisine,
    Feature,
    Hall,
    Place,
    PlaceFeature,
    PlaceImage,
    PlaceType,
    PlaceUpdateRequest,
    Reservation,
    Table,
    Tag,
)
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator

from users.models import CustomUser


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = [
            "type",
            "name",
            "city",
            "street_type",
            "street_name",
            "house_number",
            "phone",
            "facebook",
            "instagram",
            "telegram",
            "whatsapp",
            "vkontakte",
            "odnoklassniki",
            "contact_email",
            "service_email",
            "website",
            "cuisines",
            "description",
            "short_description",
            "average_check",
            "features",
            "tags",
            "capacity",
            "is_active",
            "manager",
        ]
        widgets = {
            "type": forms.Select(),
            "name": forms.TextInput(attrs={"maxlength": 100}),
            "city": forms.Select(),
            "street_type": forms.Select(),
            "street_name": forms.TextInput(attrs={"maxlength": 255}),
            "house_number": forms.TextInput(attrs={"maxlength": 10}),
            "phone": forms.TextInput(attrs={"placeholder": "+7", "maxlength": 12}),
            "facebook": forms.URLInput(),
            "instagram": forms.URLInput(),
            "telegram": forms.URLInput(),
            "whatsapp": forms.TextInput(attrs={"maxlength": 12}),
            "vkontakte": forms.URLInput(),
            "odnoklassniki": forms.URLInput(),
            "contact_email": forms.EmailInput(),
            "service_email": forms.EmailInput(),
            "website": forms.URLInput(),
            "cuisines": forms.CheckboxSelectMultiple(),
            "description": forms.Textarea(attrs={"rows": 3}),
            "short_description": forms.TextInput(attrs={"maxlength": 255}),
            "average_check": forms.NumberInput(attrs={"min": 0}),
            "features": forms.CheckboxSelectMultiple(),
            "tags": forms.CheckboxSelectMultiple(),
            "capacity": forms.NumberInput(),
            "is_active": forms.CheckboxInput(),
            "manager": forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # Получаем пользователя из kwargs
        super().__init__(*args, **kwargs)

        # Добавление общих классов к виджетам полей формы
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs["class"] = "form-control"
            elif not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs["class"] = "form-control"

        # Если пользователь не администратор, скрываем определенные поля
        if not self.user.is_admin:
            self.fields.pop("tags", None)
            self.fields.pop("manager", None)
            self.fields.pop("is_active", None)

        # Добавление класса 'is-invalid' к полям с ошибками
        if self.errors.get(field_name):
            field.widget.attrs["class"] += " is-invalid"

        # Установка начального значения для нового объекта
        if not self.instance.pk and not self.initial.get("phone"):
            self.fields["phone"].initial = "+7"

    def clean(self):
        cleaned_data = super().clean()

        # Проверка, если пользователь не администратор, исключить админские поля
        if not self.user.is_admin:
            for field in ["tags", "is_active", "manager"]:
                if field not in self.data:
                    cleaned_data.pop(field, None)

        return cleaned_data

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not phone.startswith("+7"):
            phone = "+7" + phone.lstrip("8")
        if len(phone) < 12:
            raise forms.ValidationError(
                "Номер телефона должен быть не менее 12 символов."
            )
        return phone


class PlaceUpdateRequestForm(forms.ModelForm):
    class Meta:
        model = PlaceUpdateRequest
        fields = [
            "updated_name",
            "updated_street_type",
            "updated_street_name",
            "updated_house_number",
            "updated_phone",
            "updated_facebook",
            "updated_instagram",
            "updated_telegram",
            "updated_whatsapp",
            "updated_vkontakte",
            "updated_website",
            "updated_description",
            "updated_short_description",
            "updated_average_check",
            "updated_features",
            "updated_tags",
            "updated_capacity",
            "updated_cover_image",
        ]


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "customer_name",
            "customer_phone",
            "customer_email",
            "date",
            "time",
            "guests",
            "wishes",
            "status",
        ]


class PlaceCreationForm(forms.ModelForm):
    owner_name = forms.CharField(max_length=50, label="Имя и фамилия")
    owner_email = forms.EmailField(label="Ваш email")

    class Meta:
        model = Place
        fields = ["name", "city", "phone"]

    def save(self, commit=True):
        place = super().save(commit=False)
        owner_name = self.cleaned_data["owner_name"]
        owner_email = self.cleaned_data["owner_email"]

        if commit:
            place.save()

        return place


class PlaceImageForm(forms.ModelForm):
    class Meta:
        model = PlaceImage
        fields = ["image", "is_cover"]


class CityCreateForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ["name", "image"]


class CityUpdateForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ["name", "image", "slug"]


class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ["name", "image", "slug"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
        }


class CuisineCreateForm(forms.ModelForm):
    class Meta:
        model = Cuisine
        fields = ["name"]


class CuisineForm(forms.ModelForm):
    class Meta:
        model = Cuisine
        fields = ["name", "slug"]


class FeatureCreateForm(forms.ModelForm):
    class Meta:
        model = Feature
        fields = ["name"]  # Поля, которые будут отображаться в форме
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Название особенности",
        }


class FeatureForm(forms.ModelForm):
    class Meta:
        model = Feature
        fields = ["name", "slug"]


class TagCreateForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]  # Поля, которые будут отображаться в форме
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Тег",
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]


class PlaceTypeCreateForm(forms.ModelForm):
    class Meta:
        model = PlaceType
        fields = ["name"]  # Поля, которые будут отображаться в форме
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Тип заведения",
        }


class PlaceTypeForm(forms.ModelForm):
    class Meta:
        model = PlaceType
        fields = ["name", "slug"]


class AddPlaceForm(forms.ModelForm):
    owner_name = forms.CharField(max_length=50, label="Имя владельца")
    owner_email = forms.EmailField(label="Email владельца")
    owner_password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    class Meta:
        model = Place
        fields = ["name", "city", "phone"]


class PlaceRequestForm(forms.ModelForm):
    city = forms.ModelChoiceField(
        queryset=City.objects.all(), label="Город", empty_label="Выберите город"
    )

    class Meta:
        model = PlaceRequest
        fields = ["name", "city", "phone", "owner_name", "owner_email"]
        labels = {
            "name": "Название заведения",
            "city": "Город",
            "phone": "Телефон",
            "owner_name": "Имя владельца",
            "owner_email": "Email владельца",
        }


class HallForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = ["name", "kind", "hall_type", "description", "number_of_seats", "area"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "kind": forms.Select(attrs={"class": "form-control"}),
            "hall_type": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "number_of_seats": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "area": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class TableForm(forms.ModelForm):
    hall = forms.ModelChoiceField(
        queryset=Hall.objects.all(),
        label="Зал",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Table
        fields = [
            "hall",
            "name",
            "seats",
            "quantity",
            "photo",
            "min_booking_seats",
            "min_booking_period",
            "max_booking_period",
            "booking_payment",
            "booking_interval",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "seats": forms.NumberInput(attrs={"class": "form-control"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "min_booking_seats": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "min_booking_period": forms.NumberInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "max_booking_period": forms.NumberInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "booking_payment": forms.Select(attrs={"class": "form-control"}),
            "booking_interval": forms.NumberInput(
                attrs={"class": "form-control", "type": "time"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавление подсказки
        self.fields["name"].help_text = (
            "Оставьте поле пустым для автоматической генерации названия столика."
        )


class PlaceFeatureForm(forms.ModelForm):
    class Meta:
        model = PlaceFeature
        fields = ["feature", "description", "display_on_card"]
        widgets = {
            "feature": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "display_on_card": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
