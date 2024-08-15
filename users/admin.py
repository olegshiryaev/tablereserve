from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from reservations.models import Place
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Favorite


class PlaceInline(admin.TabularInline):
    model = Place.manager.through  # Use the through model of the ManyToManyField
    extra = 1  # Number of extra forms to display
    verbose_name = "Представитель заведения"
    verbose_name_plural = "Представитель заведений"


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    inlines = [PlaceInline]

    list_display = ("email", "name", "role", "phone_number", "date_joined", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "password", "role")}),
        (_("Personal Info"), {"fields": ("name", "phone_number", "avatar")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_staff",
                    "is_active",
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
                    "name",
                    "phone_number",
                    "role",
                ),
            },
        ),
    )
    filter_horizontal = ()
    search_fields = ("email", "name", "phone_number")
    ordering = ["email"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "place", "added_at")
    search_fields = ("user__email", "place__name")
    list_filter = ("user", "place")


class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0
    raw_id_fields = ("user",)


admin.site.register(CustomUser, CustomUserAdmin)
