from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from .models import City


class RestrictAdminByIPMiddleware:
    ALLOWED_IPS = ["127.0.0.1", "91.122.208.69"]  # Укажите доверенные IP-адреса

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/secure-admin/"):
            ip = request.META.get("REMOTE_ADDR")
            if ip not in self.ALLOWED_IPS:
                return HttpResponseForbidden("Access Denied")
        return self.get_response(request)


class CityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path_parts = request.path.split("/")
        if len(path_parts) > 1 and path_parts[1]:
            city_slug = path_parts[1]
            if City.objects.filter(slug=city_slug).exists():
                request.session["selected_city"] = city_slug
        else:
            city_slug = request.session.get("selected_city", "arh")
            if city_slug:
                return redirect(f"/{city_slug}/")
        response = self.get_response(request)
        return response
