from django.urls import path
from . import views

urlpatterns = [
    path('', views.owner_dashboard, name='owner_dashboard'),
    path('settings/', views.owner_settings, name='owner_settings'),
    path('reservations/', views.owner_reservations, name='owner_reservations'),
]