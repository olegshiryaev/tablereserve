from datetime import datetime, timedelta, time
from django.utils import timezone
import pymorphy2

# from reservations.models import WorkSchedule

morph = pymorphy2.MorphAnalyzer()


def inflect_word(word, case):
    """
    Склоняет слово в указанный падеж.
    :param word: Слово для склонения.
    :param case: Падеж, в который нужно склонить слово (например, 'gent', 'loct').
    :return: Склоненное слово или исходное слово, если не удалось склонить.
    """
    parsed_word = morph.parse(word)[0]
    inflected_word = parsed_word.inflect({case})
    if inflected_word:
        return inflected_word.word
    return word


# def get_available_booking_times(date, place_id):
#     # Определяем день недели в формате, используемом в модели (например, 'MON')
#     day_of_week = date.strftime("%a").upper()[:3]

#     try:
#         # Получаем рабочие часы для конкретного дня и заведения
#         working_hours = WorkSchedule.objects.get(day=day_of_week, place_id=place_id)
#     except WorkSchedule.DoesNotExist:
#         return []

#     if working_hours.is_closed:
#         return []

#     # Преобразуем время открытия и закрытия в datetime для текущей даты
#     open_time = datetime.combine(date, working_hours.open_time)
#     close_time = datetime.combine(date, working_hours.close_time)

#     if close_time <= open_time:
#         close_time += timedelta(
#             days=1
#         )  # Обработка случаев, когда закрытие после полуночи

#     # Получаем текущее время
#     now = datetime.now()
#     now_date = now.date()
#     now_time = now.time()

#     if date == now_date:  # Если выбранный день - сегодня
#         # Определяем ближайшее время с учетом текущего времени
#         if now_time < working_hours.open_time:
#             current_time = working_hours.open_time
#         else:
#             # Округляем время до ближайшего 30-минутного интервала
#             minutes = (now_time.minute + 30) // 30 * 30
#             if minutes == 60:
#                 minutes = 0
#                 now_time = now_time.replace(hour=now_time.hour + 1, minute=minutes)
#             else:
#                 now_time = now_time.replace(minute=minutes)
#             current_time = max(
#                 datetime.combine(date, now_time).time(), working_hours.open_time
#             )
#     else:
#         current_time = working_hours.open_time

#     # Преобразуем current_time обратно в datetime для удобства работы
#     current_time = datetime.combine(date, current_time)

#     booking_intervals = []
#     while current_time.time() < close_time.time():
#         booking_intervals.append(current_time.time())
#         current_time += timedelta(minutes=30)

#     return booking_intervals


def calculate_available_time_slots(place, selected_date):
    if place is None:
        return []

    day_name = selected_date.strftime("%a").upper()  # Получаем название дня недели
    work_schedule = place.work_schedule.filter(day=day_name).first()

    if not work_schedule or work_schedule.is_closed:
        return []

    # Время открытия и закрытия
    open_time = work_schedule.open_time
    close_time = work_schedule.close_time

    # Если заведение закрывается после полуночи (в другой день)
    next_day_close_time = None
    if close_time < open_time:
        next_day_close_time = close_time
        close_time = time(23, 59)  # Завершение работы в текущий день

    # Генерация временных слотов
    time_slots = []
    current_time = datetime.combine(selected_date, open_time)
    end_time = datetime.combine(selected_date, close_time)

    while current_time <= end_time:
        time_slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=30)  # Интервал в 30 минут

    # Если заведение закрывается после полуночи, добавляем слоты следующего дня
    if next_day_close_time:
        next_day_date = selected_date + timedelta(days=1)
        current_time = datetime.combine(next_day_date, time(0, 0))
        end_time = datetime.combine(next_day_date, next_day_close_time)

        while current_time <= end_time:
            time_slots.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=30)

    return time_slots
