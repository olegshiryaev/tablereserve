from datetime import datetime, date, timedelta
from django.utils import timezone
from django import forms
from .models import Place, Reservation, Review, WorkSchedule


class WorkScheduleForm(forms.ModelForm):
    copy_to_all = forms.BooleanField(
        required=False,
        label="Скопировать на все дни",
        help_text="Отметьте, чтобы скопировать расписание на все остальные дни недели.",
    )

    class Meta:
        model = WorkSchedule
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        is_closed = cleaned_data.get("is_closed")
        open_time = cleaned_data.get("open_time")
        close_time = cleaned_data.get("close_time")

        if is_closed:
            cleaned_data["open_time"] = None
            cleaned_data["close_time"] = None
        else:
            if not open_time or not close_time:
                raise forms.ValidationError(
                    "Введите время открытия и закрытия или отметьте, что заведение в этот день закрыто."
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

        if self.cleaned_data.get("copy_to_all"):
            # Копируем расписание на все остальные дни недели, кроме текущего
            WorkSchedule.objects.filter(place=instance.place).exclude(
                day=instance.day
            ).update(
                open_time=instance.open_time,
                close_time=instance.close_time,
                is_closed=instance.is_closed,
            )

        return instance


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "text"]


class ReservationForm(forms.ModelForm):
    guests = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 16)],
        initial=2,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Reservation
        fields = [
            "date",
            "time",
            "guests",
            "customer_name",
            "customer_phone",
            "customer_email",
            "wishes",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                    "min": datetime.now().date().strftime("%Y-%m-%d"),
                }
            ),
            "time": forms.Select(attrs={"class": "form-control"}),
            "customer_name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+7999999999"}
            ),
            "customer_email": forms.EmailInput(attrs={"class": "form-control"}),
            "wishes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "(необязательно)",
                }
            ),
        }

    def __init__(self, place, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.place = place
        self.fields["time"].choices = self.get_time_choices()

        # Установка данных пользователя, если он авторизован
        if user and user.is_authenticated:
            self.fields["customer_name"].initial = user.profile.name or user.username
            self.fields["customer_phone"].initial = user.profile.phone_number or ""
            self.fields["customer_email"].initial = user.email

        # Настройка меток полей
        self.fields["date"].label = "Дата"
        self.fields["time"].label = "Время"
        self.fields["guests"].label = "Кол-во гостей"

        # Установка начального значения для даты и времени
        if self.instance.pk is None:  # Проверяем, создается ли новая запись
            self.fields["date"].initial = datetime.today().date()  # Текущая дата

    def get_time_choices(self):
        # Получаем дату из данных формы или из начального значения
        date_str = self.data.get(
            "booking_date", self.initial.get("booking_date", timezone.now().date())
        )

        if isinstance(date_str, str):
            # Если дата пришла как строка, преобразуем её в объект date
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                date = timezone.now().date()  # fallback в случае неверного формата
        else:
            date = date_str

        # Получаем доступные слоты
        slots = self.place.get_available_time_slots(date)
        return [(slot.strftime("%H:%M"), slot.strftime("%H:%M")) for slot in slots]


# class BookingForm(forms.ModelForm):
#     class Meta:
#         model = Reservation
#         fields = [
#             "date",
#             "time",
#             "customer_name",
#             "customer_phone",
#             "customer_email",
#             "guests",
#             "wishes",
#         ]
#         widgets = {
#             "date": forms.SelectDateWidget(),
#             "time": forms.Select(),
#         }
#         labels = {
#             "date": "Дата",
#             "time": "Время",
#             "customer_name": "Ваше имя",
#             "customer_phone": "Ваш телефон",
#             "customer_email": "Ваш email",
#             "guests": "Количество гостей",
#             "wishes": "Пожелания",
#         }

#     def __init__(self, *args, **kwargs):
#         available_times = kwargs.pop("available_times", [])
#         super().__init__(*args, **kwargs)
#         self.fields["time"].widget.choices = [
#             (time, time.strftime("%H:%M")) for time in available_times
#         ]


class BookingForm(forms.Form):
    booking_date = forms.DateField(
        widget=forms.SelectDateWidget, initial=timezone.now().date()
    )
    booking_time = forms.ChoiceField()

    def __init__(self, place, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.place = place
        self.fields["booking_time"].choices = self.get_time_choices()

    def get_time_choices(self):
        # Получаем дату из данных формы или из начального значения
        date_str = self.data.get(
            "booking_date", self.initial.get("booking_date", timezone.now().date())
        )

        if isinstance(date_str, str):
            # Если дата пришла как строка, преобразуем её в объект date
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                date = timezone.now().date()  # fallback в случае неверного формата
        else:
            date = date_str

        # Получаем доступные слоты
        slots = self.place.get_available_time_slots(date)
        return [(slot.strftime("%H:%M"), slot.strftime("%H:%M")) for slot in slots]
