from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


# class CustomAccountAdapter(DefaultAccountAdapter):
#     def get_login_redirect_url(self, request):
#         user = request.user
#         city_slug = request.session.get(
#             "city_slug", "arh"
#         )  # Получаем city_slug из сессии

#         if user.is_admin or user.is_owner:
#             return reverse("dashboard:place_list")
#         else:
#             return reverse("main_page", kwargs={"city_slug": city_slug})
