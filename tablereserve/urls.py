from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("secure-admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("dashboard.urls", namespace="dashboard")),
    path("", include("reservations.urls")),
    path("user/", include("users.urls", namespace="users")),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
