# characters/signals.py
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserCharacterProfile, UserTraitValue, BrainRotCharacter

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_character_profile(sender, instance, created, **kwargs):
    """Автоматически создает профиль BrainRot для нового пользователя"""
    if created:
        UserCharacterProfile.objects.create(user=instance)

@receiver(post_save, sender=UserCharacterProfile)
def assign_default_traits(sender, instance, created, **kwargs):
    """При создании профиля назначает дефолтные признаки основного персонажа"""
    if created and instance.main_character:
        # Добавляем все признаки основного персонажа
        for trait in instance.main_character.traits.all():
            UserTraitValue.objects.get_or_create(
                user_profile=instance,
                trait=trait,
                defaults={'value': trait.default_value}
            )

@receiver(pre_save, sender=UserTraitValue)
def validate_trait_value(sender, instance, **kwargs):
    """Валидация значения признака перед сохранением"""
    if instance.value < instance.trait.min_value:
        instance.value = instance.trait.min_value
    elif instance.value > instance.trait.max_value:
        instance.value = instance.trait.max_value