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
from django.utils.crypto import get_random_string
from django.conf import settings
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.validators import validate_email

from users.models import CustomUser, User


class PlaceForm(forms.ModelForm):
    # Поле для ввода email представителя при создании заведения
    representative_email = forms.EmailField(
        label="Эл. почта представителя",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        help_text="Адрес будет использован для получения доступа к личному кабинету",
    )

    class Meta:
        model = Place
        fields = [
            "type",
            "name",
            "city",
            "street_type",
            "street_name",
            "house_number",
            "floor",
            "phone",
            "facebook",
            "instagram",
            "telegram",
            "whatsapp",
            "vkontakte",
            "odnoklassniki",
            "email",
            "website",
            "cuisines",
            "description",
            "short_description",
            "average_check",
            "features",
            "tags",
            "capacity",
            "is_active",
            "is_featured",
            "manager",
        ]
        widgets = {
            "type": forms.Select(),
            "name": forms.TextInput(attrs={"maxlength": 100}),
            "city": forms.Select(),
            "street_type": forms.Select(),
            "street_name": forms.TextInput(attrs={"maxlength": 255}),
            "house_number": forms.TextInput(attrs={"maxlength": 5}),
            "floor": forms.TextInput(
                attrs={"placeholder": "Укажите, если не первый", "maxlength": 5}
            ),
            "phone": forms.TextInput(attrs={"placeholder": "+7", "maxlength": 12}),
            "facebook": forms.URLInput(),
            "instagram": forms.URLInput(),
            "telegram": forms.URLInput(),
            "whatsapp": forms.TextInput(attrs={"maxlength": 12}),
            "vkontakte": forms.URLInput(),
            "odnoklassniki": forms.URLInput(),
            "email": forms.EmailInput(),
            "website": forms.URLInput(),
            "cuisines": forms.CheckboxSelectMultiple(),
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.TextInput(attrs={"maxlength": 255}),
            "average_check": forms.NumberInput(attrs={"min": 0}),
            "features": forms.CheckboxSelectMultiple(),
            "tags": forms.CheckboxSelectMultiple(),
            "capacity": forms.NumberInput(),
            "is_active": forms.CheckboxInput(),
            "is_popular": forms.CheckboxInput(),
            "is_featured": forms.CheckboxInput(),
            "manager": forms.Select(),
        }
        help_texts = {
            "phone": "Контактный телефон для связи с заведением",
            "features": "Укажите, что ваше заведение предлагает гостям",
            "cuisines": "Укажите основные кухни, которые предлагает заведение",
            "is_active": "Показывать заведение на сайте",
            "is_featured": "Показывать заведение в рекомендованных",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields["type"].empty_label = "Выберите тип заведения"
        self.fields["city"].empty_label = "Выберите город"
        self.fields["street_type"].empty_label = "Выберите тип улицы"

        # Настройки для полей формы
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs["class"] = "form-control"
            elif not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs["class"] = "form-control"

            if self.errors.get(field_name):
                field.widget.attrs["class"] += " is-invalid"
                field.widget.attrs["aria-describedby"] = f"{field_name}-error"

        if self.instance.pk:  # Если редактирование
            if self.user.is_admin:
                self.fields["manager"] = forms.ModelChoiceField(
                    queryset=CustomUser.objects.all(),
                    label="Выберите менеджера",
                    required=False,
                    widget=forms.Select(attrs={"class": "form-control"}),
                    help_text="Выберите менеджера для заведения",
                )
            else:
                self.fields["manager"].widget = forms.HiddenInput()
        else:
            self.fields.pop("manager")  # Убираем поле manager при создании

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not phone.startswith("+7"):
            phone = "+7" + phone.lstrip("8")
        if len(phone) < 12:
            raise forms.ValidationError(
                "Номер телефона должен быть не менее 12 символов."
            )
        return phone

    def clean_representative_email(self):
        email = self.cleaned_data.get("representative_email")
        if not email:
            return None

        try:
            validate_email(email)
            user, created = CustomUser.objects.get_or_create(email=email)
            if created:
                raw_password = get_random_string(8)
                user.set_password(raw_password)
                user.username = f"User-{user.id}"
                user.role = "owner"
                user.save()

                EmailAddress.objects.create(
                    user=user, email=email, verified=False, primary=True
                )

                self.send_welcome_email(
                    user, self.cleaned_data.get("name"), raw_password
                )
                send_email_confirmation(self.request, user)
            else:
                # Если пользователь уже существует, обновляем его роль, если она не owner
                if user.role != "owner":
                    user.role = "owner"
                    user.save()  # Сохраняем изменения в роли

            return user
        except ValidationError:
            raise forms.ValidationError("Введите корректный email.")

    def send_welcome_email(self, user, place_name, raw_password):
        message = f"""
        Добрый день!

        Вы создали заведение "{place_name}" на сайте {settings.SITE_NAME}.
        Теперь Вам доступен личный кабинет для управления информацией и общения с гостями.

        Для входа в систему используйте логин и пароль ниже:
        Логин: {user.email}
        Пароль: {raw_password}

        Ссылка для входа: {self.request.build_absolute_uri(reverse("account_login"))}

        С уважением,
        Команда {settings.SITE_NAME}
        """
        send_mail(
            f"Ваша учетная запись для управления заведением {place_name}",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

    @transaction.atomic
    def save(self, commit=True):
        place = super().save(commit=False)
        if self.cleaned_data.get("representative_email"):
            place.manager = self.cleaned_data.get("representative_email")
        if commit:
            place.save()
        return place


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
        fields = ["image", "video_url", "embed_code", "description", "hall", "is_cover"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "video_url": forms.URLInput(attrs={"class": "form-control"}),
            "embed_code": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "is_cover": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hall": forms.Select(attrs={"class": "form-control"}),
        }
        help_texts = {
            "image": "Минимальные размеры изображения: 1200x800 пикселей.",
        }


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
