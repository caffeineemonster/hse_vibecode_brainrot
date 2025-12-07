# chat/consumers.py - ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для чата"""

    async def connect(self):
        """Подключение к WebSocket"""
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Группа для пользователя (личные уведомления)
        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Обновляем онлайн статус
        await self.update_presence(status='online')

        await self.accept()

    async def disconnect(self, close_code):
        """Отключение от WebSocket"""
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

        # Обновляем онлайн статус
        await self.update_presence(status='offline')

    async def receive(self, text_data):
        """Получение сообщения"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'presence':
                await self.handle_presence(data)

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")

    async def handle_chat_message(self, data):
        """Обработка сообщения чата"""
        match_id = data.get('match_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')

        try:
            match = await self.get_match(match_id)

            # Проверяем, что пользователь участник чата
            if not await self.is_participant(match):
                await self.send_error("Not a participant")
                return

            # Создаем сообщение
            message = await self.create_message(
                match=match,
                content=content,
                message_type=message_type,
                media_url=data.get('media_url')
            )

            # Отправляем сообщение другому пользователю
            other_user = await self.get_other_user(match)
            other_user_group = f"user_{other_user.id}"

            await self.channel_layer.group_send(
                other_user_group,
                {
                    'type': 'chat_message',
                    'message': await self.serialize_message(message)
                }
            )

            # Также отправляем себе для синхронизации
            await self.send(text_data=json.dumps({
                'type': 'message_sent',
                'message': await self.serialize_message(message),
                'temp_id': data.get('temp_id')
            }))

        except Exception as e:
            await self.send_error(str(e))

    async def handle_typing(self, data):
        """Обработка индикатора набора"""
        match_id = data.get('match_id')
        is_typing = data.get('is_typing', False)

        try:
            match = await self.get_match(match_id)

            if not await self.is_participant(match):
                return

            # Отправляем уведомление другому пользователю
            other_user = await self.get_other_user(match)
            other_user_group = f"user_{other_user.id}"

            await self.channel_layer.group_send(
                other_user_group,
                {
                    'type': 'typing_indicator',
                    'match_id': match_id,
                    'user_id': self.user.id,
                    'is_typing': is_typing,
                    'username': self.user.username
                }
            )

        except Exception as e:
            await self.send_error(str(e))

    async def handle_read_receipt(self, data):
        """Обработка подтверждения прочтения"""
        message_id = data.get('message_id')

        try:
            message = await self.get_message(message_id)
            match = message.match

            if not await self.is_participant(match):
                return

            # Помечаем как прочитанное
            await self.mark_as_read(message)

            # Уведомляем отправителя
            sender = message.sender
            if sender != self.user:
                sender_group = f"user_{sender.id}"

                await self.channel_layer.group_send(
                    sender_group,
                    {
                        'type': 'read_receipt',
                        'message_id': message_id,
                        'reader_id': self.user.id,
                        'read_at': timezone.now().isoformat()
                    }
                )

        except Exception as e:
            await self.send_error(str(e))

    async def handle_presence(self, data):
        """Обработка обновления статуса"""
        status = data.get('status')

        if status:
            await self.update_presence(status=status)

    async def chat_message(self, event):
        """Отправка сообщения через WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        """Отправка индикатора набора"""
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'match_id': event['match_id'],
            'user_id': event['user_id'],
            'is_typing': event['is_typing'],
            'username': event['username']
        }))

    async def read_receipt(self, event):
        """Отправка подтверждения прочтения"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'reader_id': event['reader_id'],
            'read_at': event['read_at']
        }))

    async def send_error(self, error_message):
        """Отправка ошибки"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))

    # Database methods - ЛЕНИВЫЕ ИМПОРТЫ
    @database_sync_to_async
    def get_match(self, match_id):
        from .models import Match
        return Match.objects.get(id=match_id)

    @database_sync_to_async
    def get_message(self, message_id):
        from .models import Message
        return Message.objects.get(id=message_id)

    @database_sync_to_async
    def is_participant(self, match):
        return self.user in [match.user_1, match.user_2]

    @database_sync_to_async
    def get_other_user(self, match):
        if match.user_1 == self.user:
            return match.user_2
        return match.user_1

    @database_sync_to_async
    def create_message(self, match, content, message_type, media_url=None):
        from .models import Message
        message = Message.objects.create(
            match=match,
            sender=self.user,
            content=content,
            message_type=message_type
        )
        return message

    @database_sync_to_async
    def serialize_message(self, message):
        from .serializers import MessageSerializer
        return MessageSerializer(message).data

    @database_sync_to_async
    def mark_as_read(self, message):
        if message.read_at is None:
            message.read_at = timezone.now()
            message.save()

    @database_sync_to_async
    def update_presence(self, status):
        from .models import UserPresence
        presence, created = UserPresence.objects.get_or_create(user=self.user)
        presence.status = status
        presence.last_activity = timezone.now()
        presence.save()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для уведомлений"""

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Группа для общих уведомлений пользователя
        self.user_notifications_group = f"notifications_user_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_notifications_group,
            self.channel_name
        )

        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to notifications'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'user_notifications_group'):
            await self.channel_layer.group_discard(
                self.user_notifications_group,
                self.channel_name
            )

    async def receive(self, text_data):
        # Получаем уведомления (например, о новых мэтчах, сообщениях и т.д.)
        pass

    async def send_notification(self, event):
        """Отправка уведомления"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))


class PresenceConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для онлайн статуса"""

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Группа для отслеживания онлайн статусов
        self.presence_group = "presence_updates"
        await self.channel_layer.group_add(
            self.presence_group,
            self.channel_name
        )

        await self.accept()

        # Отправляем текущий статус
        presence = await self.get_presence()
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_id': self.user.id,
            'status': presence.status if presence else 'offline'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'presence_group'):
            await self.channel_layer.group_discard(
                self.presence_group,
                self.channel_name
            )

        # Обновляем статус при отключении
        await self.update_presence('offline')

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'presence_update':
                status = data.get('status')
                if status:
                    await self.update_presence(status)

                    # Рассылаем обновление всем
                    await self.channel_layer.group_send(
                        self.presence_group,
                        {
                            'type': 'presence_broadcast',
                            'user_id': self.user.id,
                            'username': self.user.username,
                            'status': status
                        }
                    )
        except json.JSONDecodeError:
            pass

    async def presence_broadcast(self, event):
        """Рассылка обновления статуса"""
        await self.send(text_data=json.dumps({
            'type': 'presence_broadcast',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))

    @database_sync_to_async
    def get_presence(self):
        from .models import UserPresence
        return UserPresence.objects.filter(user=self.user).first()

    @database_sync_to_async
    def update_presence(self, status):
        from .models import UserPresence
        presence, created = UserPresence.objects.get_or_create(user=self.user)
        presence.status = status
        presence.last_activity = timezone.now()
        presence.save()