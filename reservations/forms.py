from datetime import datetime, date, timezone, timedelta
from django import forms
from .models import Reservation, Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['date', 'time', 'guests', 'customer_name', 'customer_phone', 'customer_email', 'wishes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'min': datetime.now().date().strftime('%Y-%m-%d')}),
            'time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7999999999'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'wishes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '(необязательно)'}),
        }

    guests = forms.ChoiceField(choices=[(i, str(i)) for i in range(1, 16)], initial=2, widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, place, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.place = place
        
        # Настройка меток полей
        self.fields['date'].label = "Дата бронирования"
        self.fields['time'].label = "Время бронирования"
        self.fields['guests'].label = "Количество гостей"

        # Установка начального значения для даты и времени
        if self.instance.pk is None:  # Проверяем, создается ли новая запись
            self.fields['date'].initial = datetime.today().date()  # Текущая дата
            current_time = datetime.now().time()
            future_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=30)).replace(second=0, microsecond=0).time()
            self.fields['time'].initial = future_time  # Текущее время + 30 минут
