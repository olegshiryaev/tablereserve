# Используем минималистичный образ Python на базе Alpine
FROM python:3.10-alpine

# Устанавливаем переменные окружения для Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Обновляем пакеты и устанавливаем зависимости
RUN apk update && apk add --no-cache libpq
RUN apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev

# Обновляем pip
RUN pip install --upgrade pip

# Создаем пользователя и группу deploy
RUN addgroup -S deploy && adduser -S deploy -G deploy

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем зависимости Python
COPY --chown=deploy:deploy requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем проект с правами пользователя deploy
COPY --chown=deploy:deploy . .

# Удаляем зависимости для сборки
RUN apk del .build-deps

# Создаем необходимые директории и настраиваем права
RUN mkdir -p /app/static /app/media /app/docker/logs \
    && chown -R deploy:deploy /app \
    && chmod -R 755 /app

# Переключаемся на пользователя deploy
USER deploy

# Команда запуска приложения
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "tablereserve.wsgi:application"]