from django import forms
from allauth.account.forms import SignupForm
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
        fields = (
            "email",
            "name",
        )
        error_messages = {
            "email": {
                "unique": "Пользователь с таким адресом электронной почты уже существует.",
            },
        }


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
