from django.dispatch import receiver
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.views import View
from dashboard.forms import (
    AddPlaceForm,
    CityCreateForm,
    CityForm,
    CityUpdateForm,
    CuisineCreateForm,
    CuisineForm,
    FeatureCreateForm,
    FeatureForm,
    PlaceCreationForm,
    PlaceForm,
    PlaceImageForm,
    PlaceRequestForm,
    PlaceTypeCreateForm,
    PlaceTypeForm,
    ReservationForm,
    TagCreateForm,
    TagForm,
)
from dashboard.models import PlaceRequest
from reservations.models import (
    City,
    Cuisine,
    Feature,
    Place,
    PlaceImage,
    PlaceType,
    Reservation,
    Tag,
)
from users.models import CustomUser
from pytils.translit import slugify
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from .mixins import AdminRequiredMixin
from django.contrib.auth import authenticate, login
from allauth.account.utils import send_email_confirmation
from allauth.account.models import EmailAddress
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save


class PlaceListView(LoginRequiredMixin, ListView):
    model = Place
    template_name = "dashboard/places_list.html"
    context_object_name = "places"
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_staff:
            return Place.objects.all()
        else:
            return Place.objects.filter(manager=self.request.user)


class PlaceDetailView(LoginRequiredMixin, DetailView):
    model = Place
    template_name = "dashboard/place_form.html"
    context_object_name = "place"

    def dispatch(self, request, *args, **kwargs):
        place = self.get_object()

        # Check if the user is an admin or the owner of the establishment
        if not request.user.is_admin and request.user not in place.manager.all():
            return HttpResponseForbidden("У вас нет прав на просмотр этой страницы.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get(
            "form", PlaceForm(instance=self.object, user=self.request.user)
        )
        context["created"] = self.request.GET.get("created", False)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = PlaceForm(
            request.POST, request.FILES, instance=self.object, user=request.user
        )
        if form.is_valid():
            place = form.save(commit=False)
            if place.name != self.object.name:
                place.slug = slugify(place.name)
            place.save()
            form.save_m2m()  # Сохранение полей ManyToMany
            return redirect("dashboard:place_detail", slug=place.slug)
        else:
            context = self.get_context_data(form=form)
            return self.render_to_response(context)


class PlaceCreateView(LoginRequiredMixin, CreateView):
    model = Place
    form_class = PlaceForm
    template_name = "dashboard/place_form.html"
    success_url = reverse_lazy("dashboard:place_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            return HttpResponseForbidden(
                "У вас нет прав на добавление нового заведения."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        # Передаем пользователя в kwargs формы
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("dashboard:place_detail", kwargs={"slug": self.object.slug})


class PlaceDeleteView(LoginRequiredMixin, DeleteView):
    model = Place
    template_name = "dashboard/place_confirm_delete.html"
    success_url = reverse_lazy("dashboard:place_list")

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, что текущий пользователь является администратором
        if not request.user.is_admin:
            return HttpResponseForbidden("У вас нет прав на удаление этого заведения.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["place"] = self.get_object()
        return context


@login_required
def reservations_list(request, place_id):
    place = get_object_or_404(Place, id=place_id)

    # Проверка, имеет ли пользователь доступ к этому заведению
    if not request.user.is_admin and place.manager != request.user:
        return redirect("dashboard:place_list")

    reservations = Reservation.objects.filter(place=place).order_by("-created_at")

    context = {
        "place": place,
        "reservations": reservations,
    }
    return render(request, "dashboard/reservations_list.html", context)


@login_required
def all_reservations(request):
    if request.user.is_admin:
        # Администратор видит все бронирования
        reservations = Reservation.objects.all().order_by("-created_at")
    else:
        # Владелец видит только бронирования своих заведений
        user_places = Place.objects.filter(manager=request.user)
        reservations = Reservation.objects.filter(place__in=user_places).order_by(
            "-created_at"
        )

    context = {
        "reservations": reservations,
    }
    return render(request, "dashboard/all_reservations.html", context)


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    place = reservation.place

    # Проверка, имеет ли пользователь доступ к этому бронированию
    if not request.user.is_admin and request.user not in place.manager.all():
        return HttpResponseForbidden(
            "У вас нет прав на просмотр и редактирование этого бронирования."
        )

    if request.method == "POST":
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            return redirect(
                "dashboard:reservation_detail", reservation_id=reservation.id
            )
    else:
        form = ReservationForm(instance=reservation)

    context = {"reservation": reservation, "place": place, "form": form}
    return render(request, "dashboard/reservation_detail.html", context)


@login_required
def place_detail(request, slug):
    place = get_object_or_404(Place, slug=slug)
    cuisines = Cuisine.objects.all()
    features = Feature.objects.all()

    # Проверяем, что текущий пользователь не является суперпользователем
    # и либо владелец заведения, либо администратором
    if not request.user.is_admin and request.user not in place.manager.all():
        return HttpResponseForbidden(
            "У вас нет прав на редактирование этого заведения."
        )

    if request.method == "POST":
        form = PlaceForm(request.POST, request.FILES, instance=place, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("dashboard:place_detail", slug=place.slug)
    else:
        form = PlaceForm(instance=place, user=request.user)

    context = {"place": place, "cuisines": cuisines, "features": features, "form": form}
    return render(request, "dashboard/place_detail.html", context)


def add_place(request):
    if request.method == "POST":
        form = PlaceRequestForm(request.POST)
        if form.is_valid():
            place_request = form.save()
            return redirect("dashboard:place_request_success")
    else:
        form = PlaceRequestForm()

    return render(
        request,
        "dashboard/add_place.html",
        {"form": form, "title": "Добавить новое заведение"},
    )


def add_place_success(request):
    return render(request, "dashboard/add_place_success.html")


class PlaceImageCreateView(CreateView):
    model = PlaceImage
    form_class = PlaceImageForm
    template_name = "dashboard/placeimage_form.html"

    def form_valid(self, form):
        place_id = self.kwargs.get("place_id")
        place = get_object_or_404(Place, id=place_id)
        form.instance.place = place
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


class PlaceImageUpdateView(UpdateView):
    model = PlaceImage
    form_class = PlaceImageForm
    template_name = "dashboard/placeimage_form.html"

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


class PlaceImageDeleteView(DeleteView):
    model = PlaceImage
    template_name = "dashboard/placeimage_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


# Представление для списка городов
class CityListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = City  # Модель, используемая для представления
    template_name = "dashboard/city_list.html"  # Шаблон для отображения списка городов

    def get_queryset(self):
        # Получаем все города с подсчетом количества заведений и сортируем по имени
        return City.objects.annotate(place_count=Count("places")).order_by("name")

    def get_context_data(self, **kwargs):
        # Добавляем дополнительный контекст в шаблон
        context = super().get_context_data(**kwargs)
        context["title"] = "Список городов"  # Заголовок страницы
        context["city_create_form"] = (
            CityCreateForm()
        )  # Форма для создания нового города
        return context


# Представление для деталей города
class CityDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = City
    template_name = "dashboard/city_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.object.name
        context["form"] = CityForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CityForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect("dashboard:city_detail", pk=self.object.pk)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        return render(
            request,
            self.template_name,
            {
                "object": self.object,
                "form": form,
                "title": f"City Detail: {self.object.name}",
            },
        )


# Представление для создания нового города
class CityCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = City  # Модель, используемая для представления
    form_class = CityCreateForm  # Форма для создания нового города
    template_name = "dashboard/city_form.html"  # Шаблон для формы создания города
    success_url = reverse_lazy(
        "dashboard:city_list"
    )  # URL для перенаправления при успешном создании

    def form_invalid(self, form):
        # Обрабатываем случай, когда форма невалидна
        response = super().form_invalid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        return response

    def form_valid(self, form):
        # Обрабатываем случай, когда форма валидна
        response = super().form_valid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return response


# Представление для удаления города
class CityDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = City  # Модель, используемая для представления
    template_name = (
        "dashboard/city_confirm_delete.html"  # Шаблон для подтверждения удаления города
    )
    success_url = reverse_lazy(
        "dashboard:city_list"
    )  # URL для перенаправления после успешного удаления

    def delete(self, request, *args, **kwargs):
        # Обрабатываем DELETE-запрос для удаления города
        self.object = self.get_object()
        self.object.delete()
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().delete(request, *args, **kwargs)


class CuisineListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Cuisine  # Модель, используемая для представления
    template_name = (
        "dashboard/cuisine_list.html"  # Шаблон для отображения списка кухонь
    )

    def get_queryset(self):
        # Получаем все кухни с подсчетом количества заведений и сортируем по имени
        return Cuisine.objects.annotate(place_count=Count("places")).order_by("name")

    def get_context_data(self, **kwargs):
        # Добавляем дополнительный контекст в шаблон
        context = super().get_context_data(**kwargs)
        context["title"] = "Список кухонь"  # Заголовок страницы
        context["cuisine_create_form"] = CuisineCreateForm()
        return context


class CuisineDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Cuisine
    template_name = "dashboard/cuisine_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.object.name
        context["form"] = CuisineForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CuisineForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect("dashboard:cuisine_detail", pk=self.object.pk)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        return render(
            request,
            self.template_name,
            {
                "object": self.object,
                "form": form,
                "title": f"Cuisine Detail: {self.object.name}",
            },
        )


class CuisineCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Cuisine
    form_class = CuisineCreateForm
    template_name = "dashboard/cuisine_form.html"
    success_url = reverse_lazy("dashboard:cuisine_list")

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        return response

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return response


class CuisineDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Cuisine
    template_name = "dashboard/cuisine_confirm_delete.html"
    success_url = reverse_lazy("dashboard:cuisine_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().delete(request, *args, **kwargs)


class FeatureListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Feature  # Модель, используемая для представления
    template_name = (
        "dashboard/feature_list.html"  # Шаблон для отображения списка особенностей
    )

    def get_queryset(self):
        # Получаем все особенности и сортируем по имени
        return Feature.objects.order_by("name")

    def get_context_data(self, **kwargs):
        # Добавляем дополнительный контекст в шаблон
        context = super().get_context_data(**kwargs)
        context["title"] = "Список особенностей"  # Заголовок страницы
        context["feature_create_form"] = (
            FeatureCreateForm()
        )  # Форма для создания новой особенности
        return context


class FeatureDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Feature
    template_name = "dashboard/feature_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.object.name
        context["form"] = FeatureForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = FeatureForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect("dashboard:feature_detail", pk=self.object.pk)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        return render(
            request,
            self.template_name,
            {
                "object": self.object,
                "form": form,
                "title": f"Feature Detail: {self.object.name}",
            },
        )


class FeatureCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Feature  # Модель, используемая для представления
    form_class = FeatureCreateForm  # Форма для создания новой особенности
    template_name = (
        "dashboard/feature_form.html"  # Шаблон для формы создания особенности
    )
    success_url = reverse_lazy(
        "dashboard:feature_list"
    )  # URL для перенаправления при успешном создании

    def form_invalid(self, form):
        # Обрабатываем случай, когда форма невалидна
        response = super().form_invalid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        return response

    def form_valid(self, form):
        # Обрабатываем случай, когда форма валидна
        response = super().form_valid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return response


class FeatureDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Feature  # Модель, используемая для представления
    template_name = "dashboard/feature_confirm_delete.html"  # Шаблон для подтверждения удаления особенности
    success_url = reverse_lazy(
        "dashboard:feature_list"
    )  # URL для перенаправления после успешного удаления

    def delete(self, request, *args, **kwargs):
        # Обрабатываем DELETE-запрос для удаления особенности
        self.object = self.get_object()
        self.object.delete()
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().delete(request, *args, **kwargs)


class TagListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Tag
    template_name = "dashboard/tag_list.html"

    def get_queryset(self):
        return Tag.objects.annotate(place_count=Count("places")).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Список тегов"
        context["tag_create_form"] = TagCreateForm()
        return context


class TagDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Tag
    template_name = "dashboard/tag_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.object.name
        context["form"] = TagForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = TagForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect("dashboard:tag_detail", pk=self.object.pk)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        return render(
            request,
            self.template_name,
            {
                "object": self.object,
                "form": form,
                "title": f"Tag Detail: {self.object.name}",
            },
        )


class TagCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Tag
    form_class = TagCreateForm
    template_name = "dashboard/tag_form.html"
    success_url = reverse_lazy("dashboard:tag_list")

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        return response

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return response


class TagDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Tag
    template_name = "dashboard/tag_confirm_delete.html"
    success_url = reverse_lazy("dashboard:tag_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().delete(request, *args, **kwargs)


# Представление для списка городов
class PlaceTypeListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = PlaceType  # Модель, используемая для представления
    template_name = (
        "dashboard/placetype_list.html"  # Шаблон для отображения списка городов
    )

    def get_queryset(self):
        # Получаем все города с подсчетом количества заведений и сортируем по имени
        return PlaceType.objects.annotate(place_count=Count("places")).order_by("name")

    def get_context_data(self, **kwargs):
        # Добавляем дополнительный контекст в шаблон
        context = super().get_context_data(**kwargs)
        context["title"] = "Типы заведений"  # Заголовок страницы
        context["placetype_create_form"] = (
            PlaceTypeCreateForm()
        )  # Форма для создания нового города
        return context


# Представление для деталей города
class PlaceTypeDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = PlaceType
    template_name = "dashboard/placetype_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.object.name
        context["form"] = PlaceTypeForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CityForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect("dashboard:placetype_detail", pk=self.object.pk)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        return render(
            request,
            self.template_name,
            {
                "object": self.object,
                "form": form,
                "title": f"City Detail: {self.object.name}",
            },
        )


# Представление для создания нового города
class PlaceTypeCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = PlaceType  # Модель, используемая для представления
    form_class = PlaceTypeCreateForm  # Форма для создания нового города
    template_name = "dashboard/placetype_form.html"  # Шаблон для формы создания города
    success_url = reverse_lazy(
        "dashboard:placetype_list"
    )  # URL для перенаправления при успешном создании

    def form_invalid(self, form):
        # Обрабатываем случай, когда форма невалидна
        response = super().form_invalid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        return response

    def form_valid(self, form):
        # Обрабатываем случай, когда форма валидна
        response = super().form_valid(form)
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return response


# Представление для удаления города
class PlaceTypeDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = PlaceType  # Модель, используемая для представления
    template_name = "dashboard/placetype_confirm_delete.html"  # Шаблон для подтверждения удаления города
    success_url = reverse_lazy(
        "dashboard:placetype_list"
    )  # URL для перенаправления после успешного удаления

    def delete(self, request, *args, **kwargs):
        # Обрабатываем DELETE-запрос для удаления города
        self.object = self.get_object()
        self.object.delete()
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().delete(request, *args, **kwargs)


def is_admin(user):
    return user.is_superuser


@user_passes_test(is_admin)
def review_place_requests(request):
    requests = PlaceRequest.objects.all()
    return render(
        request, "dashboard/review_place_requests.html", {"requests": requests}
    )


@user_passes_test(is_admin)
def approve_place_request(request, request_id):
    place_request = get_object_or_404(PlaceRequest, pk=request_id)
    if place_request.status == "pending":
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=place_request.owner_email,
            defaults={"name": place_request.owner_name, "role": "owner"},
        )

        if created:
            # Установите пароль автоматически после подтверждения email
            password = get_random_string(length=8)
            user.set_password(password)
            user.save()

            email_address, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"verified": False, "primary": True},
            )
            if created:
                send_email_confirmation(
                    request, user
                )  # Отправка только письма с подтверждением

        # Создание заведения
        place = Place.objects.create(
            name=place_request.name, city=place_request.city, phone=place_request.phone
        )
        place.manager.add(user)
        place.save()

        # Обновление статуса заявки
        place_request.status = "approved"
        place_request.save()

    return redirect("dashboard:review_place_requests")


@user_passes_test(is_admin)
def reject_place_request(request, request_id):
    place_request = PlaceRequest.objects.get(pk=request_id)
    if place_request.status == "pending":
        place_request.status = "rejected"
        place_request.save()
    return redirect("dashboard:review_place_requests")


def place_request_success(request):
    return render(request, "dashboard/place_request_success.html")


def send_password_email(email, password):
    subject = "Ваш новый пароль"
    message = render_to_string(
        "emails/new_account_password.html", {"password": password}
    )
    send_mail(subject, message, "oashiryaev@yandex.ru", [email])
