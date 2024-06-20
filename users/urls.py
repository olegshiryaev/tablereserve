from django.urls import path
from .views import toggle_favorite

urlpatterns = [
    path('toggle_favorite/', toggle_favorite, name='toggle_favorite'),
]