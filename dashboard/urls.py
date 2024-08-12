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
    path("add_place/", views.add_place, name="add_place"),
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
    # City URLs
    path("dashboard/cities/", views.CityListView.as_view(), name="city_list"),
    path(
        "dashboard/cities/<int:pk>/", views.CityDetailView.as_view(), name="city_detail"
    ),
    path("dashboard/cities/add/", views.CityCreateView.as_view(), name="city_create"),
    path(
        "dashboard/cities/<int:pk>/delete/",
        views.CityDeleteView.as_view(),
        name="city_delete",
    ),
    path("dashboard/cuisines/", views.CuisineListView.as_view(), name="cuisine_list"),
    path(
        "dashboard/cuisines/<int:pk>/",
        views.CuisineDetailView.as_view(),
        name="cuisine_detail",
    ),
    path(
        "dashboard/cuisines/create/",
        views.CuisineCreateView.as_view(),
        name="cuisine_create",
    ),
    path(
        "dashboard/cuisines/delete/<int:pk>/",
        views.CuisineDeleteView.as_view(),
        name="cuisine_delete",
    ),
    path("dashboard/features/", views.FeatureListView.as_view(), name="feature_list"),
    path(
        "dashboard/features/<int:pk>/",
        views.FeatureDetailView.as_view(),
        name="feature_detail",
    ),
    path(
        "dashboard/features/create/",
        views.FeatureCreateView.as_view(),
        name="feature_create",
    ),
    path(
        "dashboard/features/<int:pk>/delete/",
        views.FeatureDeleteView.as_view(),
        name="feature_delete",
    ),
    path("dashboard/tags/", views.TagListView.as_view(), name="tag_list"),
    path("dashboard/tags/<int:pk>/", views.TagDetailView.as_view(), name="tag_detail"),
    path("dashboard/tags/create/", views.TagCreateView.as_view(), name="tag_create"),
    path(
        "dashboard/tags/<int:pk>/delete/",
        views.TagDeleteView.as_view(),
        name="tag_delete",
    ),
    path(
        "dashboard/placetypes/",
        views.PlaceTypeListView.as_view(),
        name="placetype_list",
    ),
    path(
        "dashboard/placetypes/<int:pk>/",
        views.PlaceTypeDetailView.as_view(),
        name="placetype_detail",
    ),
    path(
        "dashboard/placetypes/create/",
        views.PlaceTypeCreateView.as_view(),
        name="placetype_create",
    ),
    path(
        "dashboard/placetypes/<int:pk>/delete/",
        views.PlaceTypeDeleteView.as_view(),
        name="placetype_delete",
    ),
]
