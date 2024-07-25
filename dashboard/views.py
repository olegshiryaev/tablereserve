from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views import View
from dashboard.forms import (
    PlaceCreationForm,
    PlaceForm,
    PlaceImageForm,
    ReservationForm,
)
from reservations.models import (
    Cuisine,
    Feature,
    Place,
    PlaceImage,
    PlaceType,
    Reservation,
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
from django.urls import reverse_lazy


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PlaceForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = PlaceForm(request.POST, request.FILES, instance=self.object)
        if form.is_valid():
            place = form.save(commit=False)
            if place.name != self.object.name:
                place.slug = slugify(place.name)
            place.save()
            form.save_m2m()  # Сохранение полей ManyToMany
            return redirect("dashboard:place_detail", slug=self.object.slug)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class PlaceCreateView(LoginRequiredMixin, CreateView):
    model = Place
    form_class = PlaceForm
    template_name = "dashboard/place_form.html"
    success_url = reverse_lazy("dashboard:place_list")

    def form_valid(self, form):
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("dashboard:place_detail", kwargs={"slug": self.object.slug})


class PlaceDeleteView(LoginRequiredMixin, DeleteView):
    model = Place
    template_name = "dashboard/place_confirm_delete.html"
    success_url = reverse_lazy("dashboard:place_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["place"] = self.get_object()
        return context


@login_required
def reservations_list(request, place_id):
    place = get_object_or_404(Place, id=place_id)

    # Проверка, имеет ли пользователь доступ к этому заведению
    if not request.user.is_staff and place.manager != request.user:
        return redirect("places_list")

    reservations = Reservation.objects.filter(place=place).order_by("-created_at")

    context = {
        "place": place,
        "reservations": reservations,
    }
    return render(request, "dashboard/reservations_list.html", context)


@login_required
def all_reservations(request):
    if request.user.is_staff:
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
    if not request.user.is_staff and reservation.place.manager != request.user:
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
    if not request.user.is_superuser and not (
        place.manager == request.user or request.user.is_staff
    ):
        return HttpResponseForbidden(
            "У вас нет прав на редактирование этого заведения."
        )

    if request.method == "POST":
        form = PlaceForm(request.POST, request.FILES, instance=place)
        if form.is_valid():
            form.save()
            return redirect("dashboard:place_detail", slug=place.slug)
    else:
        form = PlaceForm(instance=place)

    context = {"place": place, "cuisines": cuisines, "features": features, "form": form}
    return render(request, "dashboard/place_detail.html", context)


def add_place(request):
    if request.method == "POST":
        form = PlaceCreationForm(request.POST)
        if form.is_valid():
            place = form.save(commit=False)
            owner_email = form.cleaned_data["owner_email"]
            owner_password = form.cleaned_data["owner_password"]
            owner_name = form.cleaned_data["owner_name"]

            owner = CustomUser.objects.create(
                name=owner_name, email=owner_email, role="owner", is_active=False
            )
            owner.set_password(owner_password)
            owner.save()

            place.save()
            place.manager.add(owner)

            # Отправка активационного письма
            current_site = get_current_site(request)
            mail_subject = "Активируйте вашу учетную запись"
            message = render_to_string(
                "users/activation_email.html",
                {
                    "user": owner,
                    "domain": current_site.domain,
                    "uid": urlsafe_base64_encode(force_bytes(owner.pk)),
                    "token": default_token_generator.make_token(owner),
                },
            )
            send_mail(mail_subject, message, "oashiryaev@yandex.ru", [owner_email])

            return redirect("dashboard/add_place_success")
    else:
        form = AddPlaceForm()

    return render(request, "dashboard/add_place.html", {"form": form})


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
