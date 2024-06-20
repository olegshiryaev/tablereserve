from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')
        error_messages = {
            'email': {
                'unique': "Пользователь с таким адресом электронной почты уже существует.",
            },
        }


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        error_messages = {
            'email': {
                'unique': "Пользователь с таким адресом электронной почты уже существует.",
            },
        }
