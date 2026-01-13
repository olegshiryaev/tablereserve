from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import CustomUser, Profile
from locations.models import City


User = get_user_model()

class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Email"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Пароль"})


class CustomSignupForm(forms.ModelForm):
    name = forms.CharField(
        max_length=30,
        label="Имя и фамилия",
        required=True,
    )
    email = forms.EmailField(
        label="Email",
        required=True,
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self, commit=True):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
        )

        user.profile.name = self.cleaned_data["name"]
        user.profile.save()

        return user


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class ProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label="Имя пользователя", required=False)
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label="Не указано",
        label="Город",
    )

    class Meta:
        model = Profile
        fields = ["name", "phone_number", "avatar", "bio", "gender", "birth_date", "city", "email_notifications"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "phone_number": forms.TextInput(attrs={"placeholder": "+7 (___) ___-__-__"}),
            "birth_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "email_notifications": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.user:
            self.fields["username"].initial = self.instance.user.username
        if self.instance.phone_number:
            self.fields["phone_number"].initial = self.instance.phone_number
        else:
            self.fields["phone_number"].initial = "+7"

    def save(self, commit=True):
        profile = super().save(commit=False)
        username = self.cleaned_data.get("username")
        if not username:
            profile.user.username = f"User-{profile.user.id}"
        else:
            profile.user.username = username
        if commit:
            profile.user.save()
            profile.save()
        return profile