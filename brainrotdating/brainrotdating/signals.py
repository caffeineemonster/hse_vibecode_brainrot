# chat/signals.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Match, Message, UserPresence, ChatSettings

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_chat_objects(sender, instance, created, **kwargs):
    """Создание объектов чата для нового пользователя"""
    if created:
        # Создаем настройки чата
        ChatSettings.objects.create(user=instance)

        # Создаем онлайн статус
        UserPresence.objects.create(user=instance)


@receiver(post_save, sender=Match)
def handle_match_creation(sender, instance, created, **kwargs):
    """Обработка создания мэтча"""
    if created:
        # Отправляем уведомление второму пользователю
        send_match_notification(instance)


@receiver(post_save, sender=Message)
def handle_message_sent(sender, instance, created, **kwargs):
    """Обработка отправки сообщения"""
    if created and not instance.is_deleted:
        # Обновляем время последнего сообщения
        instance.match.last_message_at = instance.sent_at
        instance.match.save(update_fields=['last_message_at'])

        # Отправляем push-уведомление
        send_message_notification(instance)


@receiver(post_save, sender=UserPresence)
def handle_presence_update(sender, instance, **kwargs):
    """Обработка обновления онлайн статуса"""
    # Отправляем обновление статуса всем контактам
    notify_contacts_of_presence(instance)


def send_match_notification(match):
    """Отправка уведомления о новом мэтче"""
    # Здесь реализация отправки push/pull уведомления
    pass


def send_message_notification(message):
    """Отправка уведомления о новом сообщении"""
    # Здесь реализация отправки push уведомления
    pass


def notify_contacts_of_presence(presence):
    """Уведомление контактов об изменении статуса"""
    # Здесь WebSocket уведомления
    pass