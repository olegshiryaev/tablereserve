from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from reservations.models import Place
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Favorite, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Профили"
    fk_name = "user"


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Поля, отображаемые в списке пользователей
    list_display = ("email", "role", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "role")
    search_fields = ("email",)
    ordering = ("email",)

    # Настройка форм добавления/редактирования пользователя
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("role",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    # Связь инлайнового профиля с моделью пользователя
    inlines = (ProfileInline,)

    # Определение поля идентификации пользователя
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Поля, отображаемые в списке профилей
    list_display = ("user", "name", "phone_number", "date_joined", "city")
    list_filter = ("date_joined", "city")
    search_fields = ("user__email", "name", "phone_number")
    ordering = ("user__email",)


# Регистрация кастомных моделей пользователя и профиля
admin.site.unregister(Profile)
admin.site.register(Profile, ProfileAdmin)


class PlaceInline(admin.TabularInline):
    model = Place.manager.through  # Use the through model of the ManyToManyField
    extra = 1  # Number of extra forms to display
    verbose_name = "Представитель заведения"
    verbose_name_plural = "Представитель заведений"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "place", "added_at")
    search_fields = ("user__email", "place__name")
    list_filter = ("user", "place")


class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0
    raw_id_fields = ("user",)
