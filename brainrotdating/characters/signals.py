# characters/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserCharacterProfile  # ✅ Импортируем из текущего пакета

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_character_profile(sender, instance, created, **kwargs):
    """Автоматически создает профиль BrainRot для нового пользователя"""
    if created:
        UserCharacterProfile.objects.create(user=instance)