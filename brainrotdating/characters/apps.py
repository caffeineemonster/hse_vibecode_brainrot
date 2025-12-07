# characters/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CharactersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'characters'
    verbose_name = _('BrainRot Персонажи')  # Красивое название в админке

    def ready(self):
        # Импортируем сигналы
        from . import signals