from django.contrib import admin

from locations.models import City
from django.utils.html import format_html

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "image_thumbnail")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;" />', obj.image.url
            )
        return "-"

    image_thumbnail.short_description = "Image"

