FROM python:3.10-alpine

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Установка системных зависимостей
RUN apk update && apk add --no-cache \
    build-base \
    libpq \
    postgresql-dev \
    jpeg-dev \
    zlib-dev \
    libffi-dev \
    cairo-dev \
    pango-dev \
    gdk-pixbuf-dev \
    poppler-utils \
    curl \
    git \
    && python3 -m ensurepip \
    && pip3 install --upgrade pip setuptools wheel poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только файлы зависимостей (для кэширования Docker-слоя)
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости проекта
RUN poetry install --no-root

# Копируем остальной код проекта
COPY . .

# Настройка прав доступа (опционально)
RUN chmod -R 777 /app
