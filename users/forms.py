from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='First Name')

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        # Можно добавить настройки формы здесь, если необходимо
        self.fields['name'].required = True  # Необязательное поле

    def save(self, request):
        # Вы можете переопределить метод save, если необходимо выполнить дополнительные действия при сохранении формы
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['name']
        user.save()
        return user


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('email', 'name',)
        error_messages = {
            'email': {
                'unique': "Пользователь с таким адресом электронной почты уже существует.",
            },
        }


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            'email', 'name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        error_messages = {
            'email': {
                'unique': "Пользователь с таким адресом электронной почты уже существует.",
            },
        }
