# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        # Создаем профиль BrainRot
        from characters.models import UserCharacterProfile
        UserCharacterProfile.objects.create(user=instance)

        # Создаем настройки чата
        from chat.models import ChatSettings
        ChatSettings.objects.create(user=instance)