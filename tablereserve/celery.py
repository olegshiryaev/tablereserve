import os
from celery import Celery

# Устанавливаем переменную окружения для настройки Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tablereserve.settings")

# Инициализация Celery приложения
app = Celery("tablereserve")

# Загрузка конфигурации Celery из настроек Django с префиксом CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое обнаружение задач из всех зарегистрированных Django приложений
app.autodiscover_tasks()

# Повторные попытки подключения к брокеру при старте (Celery 6.0+)
app.conf.broker_connection_retry_on_startup = True
