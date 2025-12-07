# brainrotdating/admin.py (если нет - создай в корне проекта)
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.auth.models import Group

# Кастомный заголовок админки
admin.site.site_header = 'BrainRot Dating Administration'
admin.site.site_title = 'BrainRot Dating Admin'
admin.site.index_title = 'Добро пожаловать в панель управления BrainRot Dating'


# Убрать стандартную модель Group если не нужна
# admin.site.unregister(Group)

# Кастомная главная страница админки
class CustomAdminSite(admin.AdminSite):
    site_header = 'BrainRot Dating Administration'
    site_title = 'BrainRot Dating Admin Portal'
    index_title = 'Панель управления'

    def get_app_list(self, request):
        """
        Кастомный порядок приложений в админке
        """
        app_list = super().get_app_list(request)

        # Порядок приложений
        order = {
            'users': 1,
            'characters': 2,
            'auth': 3,
        }

        app_list.sort(key=lambda x: order.get(x['app_label'], 999))
        return app_list

# Если хочешь использовать кастомную админку
# admin.site = CustomAdminSite()