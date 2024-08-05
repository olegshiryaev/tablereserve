from django.contrib.auth.mixins import UserPassesTestMixin


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # Проверяем, является ли пользователь администратором
        return self.request.user.is_authenticated and self.request.user.is_admin
