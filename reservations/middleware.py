from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.conf import settings
from .models import City


class CityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Пути, в которых не нужно учитывать город
        self.excluded_paths = [
            "secure-admin/",
            "profile/",
            "accounts/",
            "dashboard/",
            "welcome/",
            "user/",
        ]

    def __call__(self, request):
        # Проверяем, не является ли путь запросом к статическим или медиафайлам
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith(
            settings.MEDIA_URL
        ):
            return self.get_response(request)

        # Проверяем, не является ли путь исключением
        for excluded_path in self.excluded_paths:
            if excluded_path in request.path:
                return self.get_response(request)

        path_parts = request.path.split("/")
        if len(path_parts) > 1 and path_parts[1]:
            city_slug = path_parts[1]
            if City.objects.filter(slug=city_slug).exists():
                request.session["selected_city"] = city_slug
            else:
                city_slug = request.session.get(
                    "selected_city", "arh"
                )  # Замена на slug города по умолчанию
                remaining_path = "/".join(path_parts[2:])
                return redirect(f"/{city_slug}/{remaining_path}")
        else:
            city_slug = request.session.get("selected_city", "arh")
            return redirect(f"/{city_slug}/")

        response = self.get_response(request)
        return response
