# forms.py
from django import forms
from reservations.models import Place, Reservation


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = [
            "type",
            "name",
            "city",
            "phone",
            "website",
            "cuisines",
            "description",
            "average_check",
            "features",
            "has_kids_room",
            "capacity",
            "cover_image",
            "is_active",
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


class AddPlaceForm(forms.ModelForm):
    owner_name = forms.CharField(max_length=50, label="Имя владельца")
    owner_email = forms.EmailField(label="Email владельца")
    owner_password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    class Meta:
        model = Place
        fields = ["name", "city", "phone"]
