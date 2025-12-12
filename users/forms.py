from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import CustomUser, Profile
from locations.models import City


class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Email"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Пароль"})


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