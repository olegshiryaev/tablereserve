# forms.py
from django import forms
from reservations.models import Place, Reservation

class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['type', 'name', 'city', 'address', 'phone', 'website', 'cuisines', 'description', 'average_check', 'features', 'has_kids_room', 'capacity', 'cover_image', 'is_active']


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['customer_name', 'customer_phone', 'customer_email', 'date', 'time', 'guests', 'wishes', 'status']