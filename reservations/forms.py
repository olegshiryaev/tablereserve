from datetime import datetime, date, timezone, timedelta
from django import forms
from .models import Reservation, Review, WorkSchedule


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['date', 'time', 'guests', 'first_name', 'last_name', 'phone', 'email', 'wishes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
            'guests': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '2'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7999999999'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'wishes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, place, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.place = place
        self.fields['date'].label = "Дата бронирования"
        self.fields['time'].label = "Время бронирования"
        self.fields['guests'].label = "Количество гостей"
        self.fields['guests'].initial = 2

        # Set initial values for date and time
        self.fields['date'].initial = datetime.today().date()
        current_time = datetime.now().time()
        future_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=30)).replace(second=0,
                                                                                                         microsecond=0).time()
        self.fields['time'].initial = future_time
