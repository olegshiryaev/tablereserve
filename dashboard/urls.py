from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/places/", views.PlaceListView.as_view(), name="place_list"),
    path("dashboard/places/new/", views.PlaceCreateView.as_view(), name="place_create"),
    path(
        "dashboard/places/<slug:slug>/",
        views.PlaceDetailView.as_view(),
        name="place_detail",
    ),
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
    path("add_place/", views.PlaceCreateView.as_view(), name="add_place"),
    path("add_place_success/", views.add_place_success, name="add_place_success"),
]
