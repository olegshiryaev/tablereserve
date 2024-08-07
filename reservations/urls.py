from django.urls import path
from . import views

urlpatterns = [
    path("<str:city_slug>/", views.main_page, name="main_page"),
    path("<str:city_slug>/places/", views.place_list, name="place_list"),
    path(
        "<str:city_slug>/places/<slug:place_slug>/",
        views.place_detail,
        name="place_detail",
    ),
    path(
        "update_time_choices/<int:place_id>/<str:date>/",
        views.update_time_choices,
        name="update_time_choices",
    ),
    path(
        "<str:city_slug>/places/<slug:place_slug>/",
        views.reserve_table,
        name="reserve_table",
    ),
    path(
        "<str:city_slug>/places/<slug:place_slug>/add_review/",
        views.add_review,
        name="add_review",
    ),
]
