# from datetime import datetime, timedelta, time

# from reservations.models import WorkSchedule


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
