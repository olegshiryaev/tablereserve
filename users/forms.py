from django import forms
from allauth.account.forms import SignupForm, LoginForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from reservations.models import City
from .models import CustomUser, Profile
from django.contrib.auth.forms import SetPasswordForm


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Email"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Пароль"}
        )


class CustomSignupForm(SignupForm):
    name = forms.CharField(max_length=50, label="Имя", required=True)
    email = forms.EmailField(label="Email", required=True)
    password1 = forms.CharField(
        widget=forms.PasswordInput(), label="Пароль", required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Имя"}
        )
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Email"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Пароль"}
        )

    def save(self, request):
        # Сначала сохраняем пользователя
        user = super(CustomSignupForm, self).save(request)

        # Устанавливаем имя пользователя в профиль
        user.profile.name = self.cleaned_data.get("name")
        user.profile.save()

        # Генерируем имя пользователя в формате User-id
        user.username = f"User-{user.id}"

        # Сохраняем изменения в модели пользователя
        user.save()
        return user


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ("email", "password1", "password2")
        error_messages = {
            "email": {
                "unique": "Пользователь с таким адресом электронной почты уже существует.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
        error_messages = {
            "email": {
                "unique": "Пользователь с таким адресом электронной почты уже существует.",
            },
        }


class ProfileForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        label="Имя пользователя",
        required=False,
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label="Не указано",
        label="Город",
    )

    class Meta:
        model = Profile
        fields = [
            "name",
            "phone_number",
            "avatar",
            "bio",
            "gender",
            "birth_date",
            "city",
            "email_notifications",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "phone_number": forms.TextInput(
                attrs={"placeholder": "+7 (___) ___-__-__"}
            ),
            "birth_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "email_notifications": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем начальное значение username
        if self.instance and self.instance.user:
            self.fields["username"].initial = self.instance.user.username

        # Устанавливаем начальное значение +7
        if self.instance.phone_number:
            self.fields["phone_number"].initial = self.instance.phone_number
        else:
            self.fields["phone_number"].initial = "+7"

    def save(self, commit=True):
        profile = super().save(commit=False)
        # Обновляем имя пользователя
        username = self.cleaned_data.get("username")
        if not username:  # If the username is not provided
            profile.user.username = f"User-{profile.user.id}"
        else:
            profile.user.username = username

        if commit:
            profile.user.save()
            profile.save()
        return profile
