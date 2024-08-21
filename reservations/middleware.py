from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from .models import City


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
