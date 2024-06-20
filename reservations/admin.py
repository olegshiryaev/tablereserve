from django.contrib import admin
from .models import City, Cuisine, Discount, Feature, Place, PlaceImage, Menu, MenuItem, PlaceType, Review, Reservation, \
    ReviewImage, Table, WorkSchedule, Event


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['name']
    list_filter = ['name']
    search_fields = ['name']

    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
    )


class FeatureInline(admin.TabularInline):
    model = Place.features.through
    extra = 1


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule


@admin.register(PlaceType)
class PlaceTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'city', 'type', 'address', 'phone', 'website', 'average_check', 'capacity', 'rating', 'is_active')
    search_fields = ('name', 'city__name', 'address', 'phone')
    list_filter = ('city', 'type', 'is_active')
    inlines = [FeatureInline]
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PlaceImage)
class PlaceImageAdmin(admin.ModelAdmin):
    list_display = ('place', 'image', 'is_cover')
    list_filter = ('is_cover',)


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'opening_time', 'closing_time', 'is_closed')
    list_filter = ('weekday', 'is_closed')


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'place', 'capacity')
    list_filter = ('place',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('number', 'user', 'place', 'table', 'date', 'time', 'guests', 'created_at', 'updated_at')
    list_filter = ('place', 'date')
    search_fields = ('number', 'user__username', 'place__name', 'table__number')


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'place')
    list_filter = ('place',)
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'menu', 'price', 'is_available')
    list_filter = ('menu', 'is_available')
    search_fields = ('name', 'menu__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'place', 'rating', 'created_at', 'is_approved', 'is_spam', 'is_inappropriate']
    list_filter = ['is_approved', 'is_spam', 'is_inappropriate']
    search_fields = ['user__username', 'place__name', 'text']
    actions = ['approve_reviews', 'mark_as_spam', 'mark_as_inappropriate']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    def mark_as_spam(self, request, queryset):
        queryset.update(is_spam=True)

    def mark_as_inappropriate(self, request, queryset):
        queryset.update(is_inappropriate=True)


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('review', 'image')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'place', 'date', 'start_time', 'end_time', 'is_active')
    list_filter = ('place', 'date', 'is_active')
    search_fields = ('name', 'place__name')


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'start_date', 'end_date', 'discount_percentage')
    list_filter = ('place', 'start_date', 'end_date')
    search_fields = ('title', 'place__name')
