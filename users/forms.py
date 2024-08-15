from django import forms
from allauth.account.forms import SignupForm, LoginForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomSignupForm(SignupForm):
    name = forms.CharField(max_length=50, label="Имя", required=True)
    email = forms.EmailField(label="Email", required=True)
    password1 = forms.CharField(
        widget=forms.PasswordInput(), label="Пароль", required=True
    )

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.name = self.cleaned_data["name"]
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
            "name",
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


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Email"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Пароль"}
        )
