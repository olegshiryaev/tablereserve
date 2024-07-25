from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/places/", views.PlaceListView.as_view(), name="place_list"),
    path("dashboard/places/add/", views.PlaceCreateView.as_view(), name="place_create"),
    path(
        "dashboard/places/<slug:slug>/",
        views.PlaceDetailView.as_view(),
        name="place_detail",
    ),
    path(
        "places/<slug:slug>/delete/",
        views.PlaceDeleteView.as_view(),
        name="place_delete",
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
    path(
        "dashboard/places/<int:place_id>/images/add/",
        views.PlaceImageCreateView.as_view(),
        name="placeimage_add",
    ),
    path(
        "dashboard/places/images/<int:pk>/edit/",
        views.PlaceImageUpdateView.as_view(),
        name="placeimage_edit",
    ),
    path(
        "dashboard/places/images/<int:pk>/delete/",
        views.PlaceImageDeleteView.as_view(),
        name="placeimage_delete",
    ),
]
