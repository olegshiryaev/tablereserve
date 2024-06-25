from datetime import datetime, date, timezone, timedelta
from django import forms
from .models import Reservation, Review, WorkSchedule


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']


class ReservationForm(forms.ModelForm):
    guests = forms.ChoiceField(choices=[(i, str(i)) for i in range(1, 16)], initial=2, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Reservation
        fields = ['date', 'time', 'guests', 'customer_name', 'customer_phone', 'customer_email', 'wishes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'min': datetime.now().date().strftime('%Y-%m-%d')}),
            'time': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7999999999'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'wishes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '(необязательно)'}),
        }

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
            self.update_time_choices(datetime.today().date())  # Установить время для текущей даты

        # Определение доступного времени для бронирования при изменении даты
        if 'date' in self.data:
            selected_date = datetime.strptime(self.data['date'], '%Y-%m-%d').date()
            self.update_time_choices(selected_date)

    def update_time_choices(self, selected_date):
        day_name = selected_date.strftime('%a').upper()
        work_schedule = WorkSchedule.objects.filter(place=self.place, day=day_name).first()

        if work_schedule:
            start_time = work_schedule.open_time
            end_time = (datetime.combine(datetime.today(), work_schedule.close_time) - timedelta(hours=1)).time()  # Закрытие за час до закрытия

            now = datetime.now()
            current_time = now.time()

            # Calculate the next half hour
            if now.minute < 30:
                next_half_hour = now.replace(minute=30, second=0, microsecond=0)
            else:
                next_half_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

            # Use either the start time or the next half hour, whichever is later
            if selected_date == now.date():
                current_time = max(next_half_hour.time(), start_time)
            else:
                current_time = start_time

            time_choices = []
            interval = timedelta(minutes=15)

            while current_time <= end_time:
                time_choices.append((current_time.strftime('%H:%M'), current_time.strftime('%H:%M')))
                current_time = (datetime.combine(datetime.today(), current_time) + interval).time()

            self.fields['time'].choices = time_choices
        else:
            self.fields['time'].choices = []  # Если расписание не найдено, очищаем список доступного времени
