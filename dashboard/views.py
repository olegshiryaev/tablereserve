from django.dispatch import receiver
from django.http import (
    Http404,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.views import View
from dashboard.forms import (
    AddPlaceForm,
    BookingSettingsForm,
    CityCreateForm,
    CityForm,
    CityUpdateForm,
    CuisineCreateForm,
    CuisineForm,
    FeatureCreateForm,
    FeatureForm,
    HallForm,
    PlaceCreationForm,
    PlaceFeatureForm,
    PlaceForm,
    PlaceImageForm,
    PlaceRequestForm,
    PlaceTypeCreateForm,
    PlaceTypeForm,
    ReservationForm,
    TableForm,
    TagCreateForm,
    TagForm,
)
from dashboard.models import PlaceRequest
from reservations.models import (
    BookingSettings,
    City,
    Cuisine,
    Feature,
    Hall,
    Place,
    PlaceFeature,
    PlaceImage,
    PlaceType,
    Reservation,
    Review,
    Table,
    Tag,
    WorkSchedule,
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
from django.views.generic import TemplateView
from django.contrib import messages


@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")


class PlaceListView(LoginRequiredMixin, ListView):
    model = Place
    template_name = "dashboard/places_list.html"
    context_object_name = "places"

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
        # Получаем объект заведения, если не найдено - автоматически выбрасывается 404
        place = get_object_or_404(Place, slug=kwargs.get("slug"))

        # Проверяем права доступа
        if not request.user.is_admin and place.manager != request.user:
            return HttpResponseForbidden("У вас нет прав на просмотр этой страницы.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        place = self.object
        context["form"] = kwargs.get(
            "form", PlaceForm(instance=self.object, user=self.request.user)
        )
        # Добавляем связанные объекты и расписание работы
        context["work_schedule"] = WorkSchedule.get_sorted_schedules(self.object.id)
        context["halls"] = self.object.halls.all().prefetch_related("tables")
        context["tables"] = Table.objects.filter(hall__place=self.object)

        # Генерация абсолютного URL
        context["absolute_url"] = self.request.build_absolute_uri(
            self.object.get_absolute_url()
        )

        # Работа с формой настроек бронирования
        booking_settings, created = BookingSettings.objects.get_or_create(place=place)
        context["booking_form"] = kwargs.get(
            "booking_form", BookingSettingsForm(instance=booking_settings)
        )

        # Сначала обложка, затем остальные изображения
        media_list = list(place.images.filter(is_cover=True)) + list(
            place.images.filter(is_cover=False)
        )
        context["media_list"] = media_list
        context["has_images"] = bool(media_list)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        place_form = PlaceForm(
            request.POST, request.FILES, instance=self.object, user=request.user
        )
        booking_form = BookingSettingsForm(
            request.POST, instance=self.object.booking_settings
        )

        if place_form.is_valid() and booking_form.is_valid():
            # Сохранение заведения
            place = place_form.save(commit=False)
            if place.name != self.object.name:
                place.slug = slugify(place.name)
            place.save()
            place_form.save_m2m()

            # Сохранение настроек бронирования
            booking_form.save()

            # Обновляем расписание работы (если необходимо)
            self.update_work_schedule(request, place)

            return redirect("dashboard:place_detail", slug=place.slug)
        else:
            context = self.get_context_data(form=place_form, booking_form=booking_form)
            return self.render_to_response(context)

    def update_work_schedule(self, request, place):
        """Обновление расписания работы заведения"""
        for schedule in place.work_schedule.all():
            open_time = request.POST.get(f"open_time_{schedule.day}")
            close_time = request.POST.get(f"close_time_{schedule.day}")
            is_closed = request.POST.get(f"is_closed_{schedule.day}") == "1"

            if is_closed:
                schedule.open_time = None
                schedule.close_time = None
                schedule.is_closed = True
            else:
                schedule.open_time = open_time
                schedule.close_time = close_time
                schedule.is_closed = False

            schedule.save()


class PlaceCreateView(CreateView):
    model = Place
    form_class = PlaceForm
    template_name = "dashboard/place_form.html"

    def get_form_kwargs(self):
        # Передаем пользователя и request в kwargs формы
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        # Генерируем slug для заведения
        form.instance.slug = slugify(form.instance.name)

        # Проверка роли пользователя
        if self.request.user.is_authenticated and self.request.user.is_admin:
            # Автоматическая верификация для администраторов
            form.instance.is_active = True
        else:
            # Для обычных пользователей и незалогиненных is_active = False
            form.instance.is_active = False

        # Сохраняем объект
        response = super().form_valid(form)

        # Возвращаем редирект после успешного сохранения
        return response

    def get_success_url(self):
        # Проверяем, является ли пользователь администратором
        if self.request.user.is_authenticated and self.request.user.is_admin:
            # Администраторы перенаправляются на детальную страницу заведения
            return reverse_lazy(
                "dashboard:place_detail", kwargs={"slug": self.object.slug}
            )

        # Для обычных пользователей или менеджеров добавляем email в URL
        email = self.object.manager.email if self.object.manager else ""
        success_url = reverse_lazy("dashboard:place_submission_success")
        return f"{success_url}?email={email}" if email else success_url


class PlaceSubmissionSuccessView(TemplateView):
    template_name = "dashboard/place_submission_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.GET.get("email")

        return context


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


class ToggleVerifiedView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin  # Только администратор может менять статус

    def post(self, request, *args, **kwargs):
        place_id = kwargs.get("pk")
        place = get_object_or_404(Place, pk=place_id)

        # Переключение статуса проверки
        place.is_active = not place.is_active
        place.save()

        # Перенаправление обратно на страницу заведения
        return redirect(reverse("dashboard:place_detail", kwargs={"slug": place.slug}))


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
    # Если пользователь является администратором
    if request.user.is_admin:
        # Администратор видит все бронирования, отсортированные по дате создания
        reservations = (
            Reservation.objects.all().select_related("place").order_by("-created_at")
        )
    else:
        # Владелец видит только бронирования своих заведений
        owner_places = Place.objects.filter(manager=request.user)
        reservations = (
            Reservation.objects.filter(place__in=owner_places)
            .select_related("place")
            .order_by("-created_at")
        )

    context = {
        "reservations": reservations,  # Передача списка бронирований в шаблон
    }
    return render(request, "dashboard/all_reservations.html", context)


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    place = reservation.place

    # Проверка, имеет ли пользователь доступ к этому бронированию
    if not request.user.is_admin and request.user != place.manager:
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
def reservation_accept(request, id):
    # Получаем бронирование по ID или 404, если не найдено
    reservation = get_object_or_404(Reservation, id=id)

    # Проверяем права доступа
    if not request.user.is_admin and reservation.place.manager != request.user:
        messages.error(request, "У вас нет прав для принятия этого бронирования.")
        return redirect("dashboard:reservation_list")

    # Меняем статус на "Подтверждено" (confirmed)
    reservation.status = "confirmed"
    reservation.save()

    # Сообщение об успешном принятии
    messages.success(request, f"Бронирование №{reservation.id} успешно подтверждено.")

    return redirect("dashboard:reservation_list")


@login_required
def reservation_reject(request, id):
    # Получаем бронирование по ID или 404, если не найдено
    reservation = get_object_or_404(Reservation, id=id)

    # Проверяем права доступа
    if not request.user.is_admin and reservation.place.manager != request.user:
        messages.error(request, "У вас нет прав для отклонения этого бронирования.")
        return redirect("dashboard:reservation_list")

    # Меняем статус на "Отменено рестораном" (cancelled_by_restaurant)
    reservation.status = "cancelled_by_restaurant"
    reservation.save()

    # Сообщение об успешном отклонении
    messages.success(request, f"Бронирование №{reservation.id} успешно отклонено.")

    return redirect("dashboard:reservation_list")


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
        place = get_object_or_404(Place, id=self.kwargs["place_id"])
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

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return JsonResponse({"success": True})


def set_cover_image(request, pk):
    image = get_object_or_404(PlaceImage, pk=pk)

    # Установим текущее изображение обложкой, сбросив предыдущие
    PlaceImage.objects.filter(place=image.place).update(is_cover=False)
    image.is_cover = True
    image.save()

    return redirect("dashboard:place_detail", slug=image.place.slug)


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
        form = CityForm(request.POST, request.FILES, instance=self.object)
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


class HallCreateView(LoginRequiredMixin, CreateView):
    model = Hall
    form_class = HallForm
    template_name = "dashboard/hall_form.html"

    def form_valid(self, form):
        form.instance.place = self.get_place()
        return super().form_valid(form)

    def get_place(self):
        place_id = self.kwargs.get("place_id")
        return Place.objects.get(id=place_id)

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.get_place().slug}
        )


class HallUpdateView(LoginRequiredMixin, UpdateView):
    model = Hall
    form_class = HallForm
    template_name = "dashboard/hall_form.html"
    context_object_name = "hall"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form", HallForm(instance=self.object))
        return context

    def form_valid(self, form):
        # При редактировании зала, не нужно привязывать его к заведению повторно,
        # так как он уже привязан через внешний ключ.
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


class HallDeleteView(LoginRequiredMixin, DeleteView):
    model = Hall
    template_name = "dashboard/hall_confirm_delete.html"
    context_object_name = "hall"

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


class TableCreateView(CreateView):
    model = Table
    form_class = TableForm
    template_name = "dashboard/table_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        place_id = self.kwargs["place_id"]
        # Ограничиваем выбор залов только теми, которые принадлежат текущему заведению
        form.fields["hall"].queryset = Hall.objects.filter(place_id=place_id)
        return form

    def form_valid(self, form):
        table = form.save()
        return redirect(
            reverse("dashboard:place_detail", kwargs={"slug": table.hall.place.slug})
        )


class TableUpdateView(UpdateView):
    model = Table
    form_class = TableForm
    template_name = "dashboard/table_form.html"

    def form_valid(self, form):
        table = form.save()
        return redirect(
            reverse("dashboard:place_detail", kwargs={"slug": table.hall.place.slug})
        )


class TableDeleteView(LoginRequiredMixin, DeleteView):
    model = Table
    template_name = "dashboard/table_confirm_delete.html"
    context_object_name = "table"

    def get_success_url(self):
        return reverse_lazy(
            "dashboard:place_detail", kwargs={"slug": self.object.hall.place.slug}
        )


class PlaceFeatureCreateView(CreateView):
    model = PlaceFeature
    form_class = PlaceFeatureForm
    template_name = "dashboard/placefeature_form.html"

    def form_valid(self, form):
        form.instance.place = get_object_or_404(Place, id=self.kwargs["place_id"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "dashboard:place_detail",
            kwargs={"slug": get_object_or_404(Place, id=self.kwargs["place_id"]).slug},
        )


class PlaceFeatureUpdateView(UpdateView):
    model = PlaceFeature
    form_class = PlaceFeatureForm
    template_name = "dashboard/placefeature_form.html"

    def get_success_url(self):
        return reverse(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


class PlaceFeatureDeleteView(DeleteView):
    model = PlaceFeature
    template_name = "dashboard/placefeature_confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "dashboard:place_detail", kwargs={"slug": self.object.place.slug}
        )


class ReviewListView(LoginRequiredMixin, ListView):
    model = Review
    template_name = "dashboard/review_list.html"
    context_object_name = "reviews"

    def get_queryset(self):
        if self.request.user.is_staff:
            # Если пользователь - администратор, получаем все отзывы
            return Review.objects.select_related("user", "place").order_by(
                "-created_at"
            )
        else:
            # Если пользователь - менеджер, получаем отзывы только по его заведениям
            return (
                Review.objects.filter(place__manager=self.request.user)
                .select_related("user")
                .order_by("-created_at")
            )
