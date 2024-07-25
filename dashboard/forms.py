# forms.py
from django import forms
from reservations.models import Place, PlaceImage, PlaceUpdateRequest, Reservation
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
            "website",
            "cuisines",
            "description",
            "short_description",
            "average_check",
            "features",
            "tags",
            "has_kids_room",
            "capacity",
            "is_active",
            "manager",
        ]
        widgets = {
            "type": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control", "maxlength": 100}),
            "city": forms.Select(attrs={"class": "form-control"}),
            "street_type": forms.Select(attrs={"class": "form-control"}),
            "street_name": forms.TextInput(
                attrs={"class": "form-control", "maxlength": 255}
            ),
            "house_number": forms.TextInput(
                attrs={"class": "form-control", "maxlength": 10}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+7", "maxlength": 12}
            ),
            "facebook": forms.URLInput(attrs={"class": "form-control"}),
            "instagram": forms.URLInput(attrs={"class": "form-control"}),
            "telegram": forms.URLInput(attrs={"class": "form-control"}),
            "whatsapp": forms.TextInput(
                attrs={"class": "form-control", "maxlength": 12}
            ),
            "vkontakte": forms.URLInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "cuisines": forms.CheckboxSelectMultiple(),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "short_description": forms.TextInput(
                attrs={"class": "form-control", "maxlength": 255}
            ),
            "average_check": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "features": forms.CheckboxSelectMultiple(),
            "tags": forms.SelectMultiple(attrs={"class": "form-control"}),
            "has_kids_room": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control"}),
            "rating": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "manager": forms.SelectMultiple(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("phone"):
            self.fields["phone"].initial = (
                "+7"  # Установка начального значения для нового объекта
            )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        if not phone.startswith("+7"):
            phone = "+7" + phone.lstrip("+7")  # Добавление +7 к номеру, если его нет
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
            "updated_has_kids_room",
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
    owner_name = forms.CharField(max_length=50, label="Имя владельца")
    owner_email = forms.EmailField(label="Email владельца")
    owner_password = forms.CharField(
        widget=forms.PasswordInput, label="Пароль владельца"
    )

    class Meta:
        model = Place
        fields = ["name", "city", "phone"]

    def save(self, commit=True):
        place = super().save(commit=False)
        owner_name = self.cleaned_data["owner_name"]
        owner_email = self.cleaned_data["owner_email"]
        owner_password = self.cleaned_data["owner_password"]

        if commit:
            place.save()
            owner = CustomUser.objects.create_user(
                email=owner_email,
                password=owner_password,
                name=owner_name,
                role="owner",
                is_active=False,
            )
            place.manager.add(owner)
            place.save()

            # Send activation email here
            self.send_activation_email(owner)

        return place

    def send_activation_email(self, user):
        # Логика отправки email для активации аккаунт

        current_site = get_current_site(self.request)
        mail_subject = "Activate your account."
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = f"http://{current_site.domain}/activate/{uid}/{token}/"
        message = render_to_string(
            "activation_email.html",
            {
                "user": user,
                "domain": current_site.domain,
                "uid": uid,
                "token": token,
            },
        )
        send_mail(mail_subject, message, "oashiryaev@yandex.ru", [user.email])


class PlaceImageForm(forms.ModelForm):
    class Meta:
        model = PlaceImage
        fields = ["image", "is_cover"]
