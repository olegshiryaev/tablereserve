from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class ActiveUserMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.user.is_authenticated:
            cache_key = f"last-seen-{request.user.id}"
            last_seen = cache.get(cache_key)

            # Обновляем кэш только если время активности больше 1 минуты
            if not last_seen or (timezone.now() - last_seen).total_seconds() > 60:
                # Обновляем время в кэше (на 5 минут)
                cache.set(cache_key, timezone.now(), 300)

                # Обновляем поле last_activity в базе данных
                request.user.last_activity = timezone.now()
                request.user.save(update_fields=["last_activity"])
