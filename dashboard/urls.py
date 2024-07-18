from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/places/", views.places_list, name="places_list"),
    path("dashboard/places/<slug:slug>/", views.place_detail, name="place_detail"),
    path("dashboard/reservations/", views.all_reservations, name="all_reservations"),
    path(
        "dashboard/reservations/<int:reservation_id>/",
        views.reservation_detail,
        name="reservation_detail",
    ),
    path(
        "dashboard/places/<int:place_id>/reservations/",
        views.reservations_list,
        name="reservations_list",
    ),
    path("add_place/", views.add_place, name="add_place"),
    path("add_place_success/", views.add_place_success, name="add_place_success"),
]
