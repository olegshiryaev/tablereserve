from datetime import datetime, date, timedelta
from django.utils import timezone
from django import forms
from .models import Place, Reservation, Review, ReviewResponse, Table, WorkSchedule


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


class ReviewResponseForm(forms.ModelForm):
    class Meta:
        model = ReviewResponse
        fields = ["text"]  # Поле для текста ответа
        widgets = {
            "text": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Напишите ваш ответ..."}
            ),
        }


class ReservationForm(forms.ModelForm):
    guests = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 16)],
        initial=2,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    table = forms.ModelChoiceField(
        queryset=Table.objects.none(),  # По умолчанию пустой QuerySet
        required=False,  # Поле не обязательно
        empty_label="Любой столик",  # Метка для пустого значения
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    consent = forms.BooleanField(
        required=True,
        initial=True,
        error_messages={
            "required": "Вы должны дать согласие на обработку персональных данных."
        },
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Reservation
        fields = [
            "date",
            "time",
            "guests",
            "table",
            "customer_name",
            "customer_phone",
            "customer_email",
            "wishes",
            "consent",
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
                    "rows": 5,
                    "placeholder": "(необязательно)",
                }
            ),
        }

    def __init__(self, place, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.place = place
        self.fields["time"].choices = self.get_time_choices()

        booking_settings = getattr(place, "booking_settings", None)

        # Установка количества гостей по умолчанию
        if booking_settings:
            self.fields["guests"].initial = booking_settings.default_guest_count
            self.configure_table_field(booking_settings)

        if user and user.is_authenticated:
            self.prefill_user_data(user)

        self.fields["date"].label = "Дата"
        self.fields["time"].label = "Время"
        self.fields["guests"].label = "Кол-во гостей"
        if "table" in self.fields:
            self.fields["table"].label = "Столик"
        self.fields["customer_email"].help_text = (
            "Укажите для получения сообщений о статусах заказа"
        )

        if self.instance.pk is None:
            self.fields["date"].initial = datetime.today().date()

    def configure_table_field(self, booking_settings):
        """
        Настраивает поле выбора столика в зависимости от доступных настроек заведения
        """
        if booking_settings.allow_table_selection:
            tables = Table.objects.filter(hall__place=self.place)
            if tables.exists():
                self.fields["table"].queryset = tables
            else:
                del self.fields["table"]
        else:
            del self.fields["table"]

    def prefill_user_data(self, user):
        """
        Предзаполняет данные клиента, если он авторизован
        """
        self.fields["customer_name"].initial = user.profile.name or ""
        self.fields["customer_phone"].initial = user.profile.phone_number or ""
        self.fields["customer_email"].initial = user.email or ""

    def get_time_choices(self):
        """
        Возвращает доступные временные слоты для бронирования, основанные на интервале
        и недоступном интервале перед текущим временем.
        """
        date_str = self.data.get(
            "booking_date", self.initial.get("booking_date", timezone.now().date())
        )

        if isinstance(date_str, str):
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                date = timezone.now().date()
        else:
            date = date_str

        booking_settings = getattr(self.place, "booking_settings", None)

        # Получаем недоступный интервал для бронирования
        unavailable_interval = (
            timedelta(minutes=booking_settings.unavailable_interval)
            if booking_settings
            else timedelta(minutes=30)
        )

        # Получаем доступные слоты
        slots = self.place.get_available_time_slots(date)

        now = datetime.now()
        if date == now.date():
            # Вычисляем время с учетом недоступного интервала
            next_available_time = now + unavailable_interval

            # Корректируем ближайший доступный слот в зависимости от шага минут
            if booking_settings:
                booking_interval = timedelta(minutes=booking_settings.booking_interval)
                # Ищем ближайший слот, который подходит по шагу
                next_available_time = next_available_time + (
                    booking_interval
                    - timedelta(
                        minutes=next_available_time.minute
                        % booking_interval.seconds
                        // 60
                    )
                )

            # Фильтруем слоты, которые начинаются после next_available_time
            slots = [slot for slot in slots if slot >= next_available_time.time()]

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
