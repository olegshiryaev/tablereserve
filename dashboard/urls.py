from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", views.dashboard_home, name="main"),
    path("dashboard/places/", views.PlaceListView.as_view(), name="place_list"),
    path("dashboard/places/add/", views.PlaceCreateView.as_view(), name="place_create"),
    path(
        "dashboard/places/success/",
        views.PlaceSubmissionSuccessView.as_view(),
        name="place_submission_success",
    ),
    path(
        "dashboard/places/requests/",
        views.review_place_requests,
        name="review_place_requests",
    ),
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
    path(
        "place/<int:pk>/toggle-verified/",
        views.ToggleVerifiedView.as_view(),
        name="toggle_verified",
    ),
    path("dashboard/reservations/", views.all_reservations, name="reservation_list"),
    path(
        "dashboard/reservations/<int:reservation_id>/",
        views.reservation_detail,
        name="reservation_detail",
    ),
    path(
        "dashboard/reservations/<int:id>/accept/",
        views.reservation_accept,
        name="reservation_accept",
    ),
    path(
        "dashboard/reservations/<int:id>/reject/",
        views.reservation_reject,
        name="reservation_reject",
    ),
    path(
        "dashboard/places/<int:place_id>/reservations/",
        views.reservations_list,
        name="reservations_list",
    ),
    path("dashboard/reviews/", views.ReviewListView.as_view(), name="review_list"),
    path("welcome/", views.add_place, name="welcome"),
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
    path(
        "place/image/<int:pk>/set_cover/",
        views.set_cover_image,
        name="placeimage_set_cover",
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
    path(
        "welcome/place-request-success/",
        views.place_request_success,
        name="place_request_success",
    ),
    path(
        "dashboard/approve-place-request/<int:request_id>/",
        views.approve_place_request,
        name="approve_place_request",
    ),
    path(
        "dashboard/reject-place-request/<int:request_id>/",
        views.reject_place_request,
        name="reject_place_request",
    ),
    path(
        "dashboard/places/<int:place_id>/hall/add/",
        views.HallCreateView.as_view(),
        name="hall_create",
    ),
    path(
        "dashboard/places/<int:place_id>/hall/<int:pk>/edit/",
        views.HallUpdateView.as_view(),
        name="hall_edit",
    ),
    path(
        "dashboard/places/<int:place_id>/hall/<int:pk>/delete/",
        views.HallDeleteView.as_view(),
        name="hall_delete",
    ),
    path(
        "dashboard/places/<int:place_id>/table/add/",
        views.TableCreateView.as_view(),
        name="table_create",
    ),
    path(
        "dashboard/places/<int:place_id>/table/<int:pk>/edit/",
        views.TableUpdateView.as_view(),
        name="table_edit",
    ),
    path(
        "dashboard/places/<int:place_id>/table/<int:pk>/delete/",
        views.TableDeleteView.as_view(),
        name="table_delete",
    ),
    path(
        "place/<int:place_id>/feature/add/",
        views.PlaceFeatureCreateView.as_view(),
        name="place_feature_add",
    ),
    path(
        "place/feature/<int:pk>/edit/",
        views.PlaceFeatureUpdateView.as_view(),
        name="place_feature_edit",
    ),
    path(
        "place/feature/<int:pk>/delete/",
        views.PlaceFeatureDeleteView.as_view(),
        name="place_feature_delete",
    ),
]
