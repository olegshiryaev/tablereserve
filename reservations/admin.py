from datetime import datetime, timedelta
from django.contrib import admin
from django.utils.html import format_html

from reservations.forms import WorkScheduleForm
from .models import (
    City,
    Cuisine,
    Discount,
    Feature,
    Place,
    PlaceFeature,
    PlaceImage,
    Menu,
    MenuItem,
    PlaceType,
    PlaceUpdateRequest,
    Review,
    Reservation,
    ReviewImage,
    Hall,
    Table,
    Tag,
    WorkSchedule,
    Event,
)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "image_thumbnail")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto;" />', obj.image.url
            )
        return "-"

    image_thumbnail.short_description = "Image"


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ["name"]
    list_filter = ["name"]
    search_fields = ["name"]

    fieldsets = ((None, {"fields": ("name",)}),)


@admin.register(PlaceFeature)
class PlaceFeatureAdmin(admin.ModelAdmin):
    list_display = ["place", "feature", "description"]


class PlaceFeatureInline(admin.TabularInline):
    model = PlaceFeature
    extra = 1


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule
    form = WorkScheduleForm
    extra = 1
    fields = ("day", "open_time", "close_time", "is_closed", "copy_to_all")
    ordering = ["day"]
    max_num = 7

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(day_order=WorkSchedule.get_day_order_annotation()).order_by(
            "day_order"
        )


class TableInline(admin.TabularInline):
    model = Table
    extra = 0


class HallInline(admin.TabularInline):
    model = Hall
    extra = 1  # Количество пустых форм для добавления новых секторов


@admin.register(PlaceType)
class PlaceTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PlaceImage)
class PlaceImageAdmin(admin.ModelAdmin):
    list_display = ("place", "image", "is_cover", "upload_date")
    search_fields = ("place__name", "sector__name")
    list_filter = ("place", "is_cover")


class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 1
    fields = ("image", "is_cover", "video_url", "embed_code", "upload_date")
    readonly_fields = ("upload_date",)
    verbose_name = "Медиа заведения"
    verbose_name_plural = "Медиа заведений"


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "type",
        "address",
        "phone",
        "website",
        "average_check",
        "capacity",
        "rating",
        "is_active",
        "cover_image_display",
        "logo_display",
    )
    search_fields = ("name", "city__name", "address", "phone", "tags__name")
    list_filter = ("city", "type", "is_active")
    inlines = [WorkScheduleInline, PlaceFeatureInline, HallInline, PlaceImageInline]
    filter_horizontal = (
        "tags",
        "cuisines",
    )
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "city",
                    "street_type",
                    "street_name",
                    "house_number",
                    "type",
                    "is_active",
                )
            },
        ),
        (
            "Контакты",
            {
                "fields": (
                    "phone",
                    "whatsapp",
                    "viber",
                    "telegram",
                    "vkontakte",
                    "odnoklassniki",
                    "instagram",
                    "facebook",
                    "contact_email",
                    "service_email",
                    "website",
                )
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "description",
                    "short_description",
                    "average_check",
                    "cuisines",
                    "tags",
                    "capacity",
                    "booking_interval",
                    "logo",
                    "rating",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("city", "type")
            .prefetch_related("cuisines", "features")
        )

    def address(self, obj):
        return f"{obj.get_street_type_display()} {obj.street_name}, {obj.house_number}"

    address.short_description = "Адрес"

    def cover_image_display(self, obj):
        return format_html(
            '<img src="{}" width="50" height="50" />', obj.get_cover_image()
        )

    cover_image_display.short_description = "Обложка"

    def logo_display(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" />', obj.logo.url)
        return "-"

    logo_display.short_description = "Логотип"


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("place", "day", "open_time", "close_time", "is_closed")
    list_filter = ("place", "day", "is_closed")
    search_fields = ("place__name",)
    form = WorkScheduleForm

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("place")

    def save_model(self, request, obj, form, change):
        # Если время закрытия до времени открытия, считается, что заведение работает до следующего дня
        if obj.close_time and obj.open_time and obj.close_time <= obj.open_time:
            obj.close_time = (
                datetime.combine(datetime.today(), obj.close_time) + timedelta(days=1)
            ).time()
        super().save_model(request, obj, form, change)


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ("name", "place", "kind", "hall_type", "number_of_seats", "area")
    search_fields = ("name", "place__name")
    list_filter = ("place", "kind", "hall_type")
    inlines = [TableInline]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "place",
                    "kind",
                    "hall_type",
                    "number_of_seats",
                    "area",
                    "description",
                )
            },
        ),
    )


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("name", "hall", "seats", "min_booking_seats", "booking_payment")
    search_fields = ("name", "hall__name", "hall__place__name")
    list_filter = ("hall", "booking_payment")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "user",
        "place",
        "table",
        "date",
        "time",
        "guests",
        "created_at",
        "updated_at",
    )
    list_filter = ("place", "date")
    search_fields = ("number", "user__username", "place__name")


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "place")
    list_filter = ("place",)
    search_fields = ("name",)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "menu", "price", "is_available")
    list_filter = ("menu", "is_available")
    search_fields = ("name", "menu__name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "place",
        "rating",
        "created_at",
        "status",
        "short_text",
    ]
    list_filter = ["status", "rating", "created_at"]
    search_fields = ["user__username", "place__name", "text"]
    actions = [
        "approve_reviews",
        "mark_as_spam",
        "mark_as_inappropriate",
        "reset_status",
    ]

    # Краткий текст отзыва (первые 50 символов)
    def short_text(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    short_text.short_description = "Текст отзыва"

    # Действия для изменения статуса
    def approve_reviews(self, request, queryset):
        queryset.update(status="approved")
        self.message_user(request, "Выбранные отзывы были одобрены.")

    def mark_as_spam(self, request, queryset):
        queryset.update(status="spam")
        self.message_user(request, "Выбранные отзывы помечены как спам.")

    def mark_as_inappropriate(self, request, queryset):
        queryset.update(status="inappropriate")
        self.message_user(request, "Выбранные отзывы помечены как неуместные.")

    def reset_status(self, request, queryset):
        queryset.update(status="pending")
        self.message_user(
            request, "Статус выбранных отзывов был сброшен на 'Ожидает модерации'."
        )

    # Название для действий в админке
    approve_reviews.short_description = "Одобрить выбранные отзывы"
    mark_as_spam.short_description = "Пометить как спам"
    mark_as_inappropriate.short_description = "Пометить как неуместные"
    reset_status.short_description = "Сбросить статус на 'Ожидает модерации'"


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ("review", "image")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "place", "date", "start_time", "end_time", "is_active")
    list_filter = ("place", "date", "is_active")
    search_fields = ("name", "place__name")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("title", "place", "start_date", "end_date", "discount_percentage")
    list_filter = ("place", "start_date", "end_date")
    search_fields = ("title", "place__name")


@admin.register(PlaceUpdateRequest)
class PlaceUpdateRequestAdmin(admin.ModelAdmin):
    list_display = ("place", "status", "submitted_by", "submitted_at")
    list_filter = ("status",)
    actions = ["approve_requests", "reject_requests"]

    def approve_requests(self, request, queryset):
        for update_request in queryset:
            update_request.approve()
            update_request.status = "approved"
            update_request.save()

    approve_requests.short_description = "Одобрить выбранные запросы"

    def reject_requests(self, request, queryset):
        queryset.update(status="rejected")

    reject_requests.short_description = "Отклонить выбранные запросы"
