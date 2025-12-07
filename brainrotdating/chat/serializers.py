# chat/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Match, Message, Reaction, ChatSettings,
    UserPresence, ChatBlock, ChatReport
)
from characters.models import BrainRotCharacter
from users.serializers import UserProfileSerializer

User = get_user_model()


class MatchUserSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор пользователя для мэтчей"""
    age = serializers.SerializerMethodField()
    brainrot_character = serializers.SerializerMethodField()
    online_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name',
                  'age', 'city', 'brainrot_character', 'online_status']

    def get_age(self, obj):
        return obj.age if hasattr(obj, 'age') else None

    def get_brainrot_character(self, obj):
        if hasattr(obj, 'brainrot_profile') and obj.brainrot_profile.main_character:
            return obj.brainrot_profile.main_character.name
        return None

    def get_online_status(self, obj):
        if hasattr(obj, 'presence'):
            return obj.presence.status
        return 'offline'


class MatchSerializer(serializers.ModelSerializer):
    """Сериализатор мэтча"""
    user_1 = MatchUserSerializer(read_only=True)
    user_2 = MatchUserSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    compatibility_display = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = ['id', 'user_1', 'user_2', 'other_user', 'status',
                  'match_type', 'compatibility_score', 'compatibility_display',
                  'created_at', 'matched_at', 'last_message_at', 'unread_count',
                  'last_message', 'is_chat_active']
        read_only_fields = ['created_at', 'matched_at', 'last_message_at']

    def get_other_user(self, obj):
        """Получить второго пользователя относительно текущего"""
        request = self.context.get('request')
        if request and request.user:
            other_user = obj.get_other_user(request.user)
            return MatchUserSerializer(other_user).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)  # <--св измените вызов
        return 0

    def get_last_message(self, obj):
        """Последнее сообщение в чате"""
        last_msg = obj.messages.filter(is_deleted=False).last()
        if last_msg:
            return {
                'content': last_msg.display_content,
                'sender': last_msg.sender.username,
                'sent_at': last_msg.sent_at,
                'type': last_msg.message_type
            }
        return None

    def get_compatibility_display(self, obj):
        """Отображение совместимости в процентах"""
        if obj.compatibility_score:
            return f"{obj.compatibility_score * 100:.0f}%"
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор сообщения"""
    sender = MatchUserSerializer(read_only=True)
    match_id = serializers.PrimaryKeyRelatedField(
        queryset=Match.objects.all(),
        write_only=True,
        source='match'
    )
    brainrot_character_info = serializers.SerializerMethodField()
    reactions_summary = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'match', 'match_id', 'sender', 'message_type',
                  'content', 'media_file', 'thumbnail', 'brainrot_character',
                  'brainrot_character_info', 'is_brainrot_reaction',
                  'is_edited', 'is_deleted', 'sent_at', 'delivered_at',
                  'read_at', 'reactions_summary', 'is_mine']
        read_only_fields = ['sent_at', 'delivered_at', 'read_at', 'sender']

    def get_brainrot_character_info(self, obj):
        """Информация о BrainRot персонаже"""
        if obj.brainrot_character:
            return {
                'id': obj.brainrot_character.id,
                'name': obj.brainrot_character.name,
                'category': obj.brainrot_character.get_category_display(),
            }
        return None

    def get_reactions_summary(self, obj):
        """Сводка реакций на сообщение"""
        reactions = obj.reactions.all()
        if reactions.exists():
            summary = {}
            for reaction in reactions:
                reaction_type = reaction.reaction_type
                summary[reaction_type] = summary.get(reaction_type, 0) + 1
            return summary
        return {}

    def get_is_mine(self, obj):
        """Принадлежит ли сообщение текущему пользователю"""
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False

    def validate(self, attrs):
        """Валидация сообщения"""
        request = self.context.get('request')

        # Проверяем, что пользователь является участником мэтча
        match = attrs.get('match')
        if request.user not in [match.user_1, match.user_2]:
            raise serializers.ValidationError("Вы не участник этого чата")

        # Проверяем, активен ли чат
        if not match.is_chat_active:
            raise serializers.ValidationError("Чат не активен")

        # Проверяем статус мэтча
        if match.status != 'accepted':
            raise serializers.ValidationError("Мэтч не подтвержден")

        # Проверяем блокировки
        if ChatBlock.objects.filter(
                blocker=match.get_other_user(request.user),
                blocked=request.user,
                is_active=True
        ).exists():
            raise serializers.ValidationError("Пользователь заблокировал вас")

        # Валидация контента
        content = attrs.get('content', '').strip()
        message_type = attrs.get('message_type', 'text')

        if message_type == 'text' and not content:
            raise serializers.ValidationError("Текстовое сообщение не может быть пустым")

        if message_type in ['image', 'video', 'audio'] and not attrs.get('media_file'):
            raise serializers.ValidationError(f"Для типа {message_type} требуется медиа файл")

        # Проверка длины текста
        if content and len(content) > 2000:
            raise serializers.ValidationError("Сообщение слишком длинное (макс. 2000 символов)")

        return attrs

    def create(self, validated_data):
        """Создание сообщения с дополнительными данными"""
        request = self.context.get('request')

        # Добавляем отправителя
        validated_data['sender'] = request.user

        # Добавляем IP и User Agent
        validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
        validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

        return super().create(validated_data)


class ReactionSerializer(serializers.ModelSerializer):
    """Сериализатор реакции"""
    user = MatchUserSerializer(read_only=True)
    message_id = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        write_only=True,
        source='message'
    )

    class Meta:
        model = Reaction
        fields = ['id', 'message', 'message_id', 'user',
                  'reaction_type', 'created_at']
        read_only_fields = ['user', 'created_at']

    def validate(self, attrs):
        """Валидация реакции"""
        request = self.context.get('request')
        message = attrs.get('message')

        # Проверяем, что пользователь является участником чата
        match = message.match
        if request.user not in [match.user_1, match.user_2]:
            raise serializers.ValidationError("Вы не участник этого чата")

        # Проверяем, что сообщение не удалено
        if message.is_deleted:
            raise serializers.ValidationError("Нельзя реагировать на удаленное сообщение")

        return attrs

    def create(self, validated_data):
        """Создание реакции"""
        request = self.context.get('request')
        validated_data['user'] = request.user

        # Удаляем старую реакцию пользователя на это сообщение
        Reaction.objects.filter(
            message=validated_data['message'],
            user=request.user
        ).delete()

        return super().create(validated_data)


class ChatSettingsSerializer(serializers.ModelSerializer):
    """Сериализатор настроек чата"""

    class Meta:
        model = ChatSettings
        fields = '__all__'
        read_only_fields = ['user', 'updated_at']


class UserPresenceSerializer(serializers.ModelSerializer):
    """Сериализатор онлайн статуса"""
    user = MatchUserSerializer(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = UserPresence
        fields = ['id', 'user', 'status', 'status_display', 'is_online',
                  'last_seen', 'last_activity', 'is_typing', 'current_chat',
                  'device_type', 'app_version', 'updated_at']
        read_only_fields = ['user', 'last_seen', 'last_activity', 'updated_at']


class ChatBlockSerializer(serializers.ModelSerializer):
    """Сериализатор блокировки"""
    blocker = MatchUserSerializer(read_only=True)
    blocked = MatchUserSerializer(read_only=True)
    blocked_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        source='blocked'
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ChatBlock
        fields = ['id', 'blocker', 'blocked', 'blocked_id', 'reason',
                  'block_type', 'created_at', 'expires_at', 'is_active']
        read_only_fields = ['blocker', 'created_at']


class ChatReportSerializer(serializers.ModelSerializer):
    """Сериализатор жалобы"""
    reporter = MatchUserSerializer(read_only=True)
    reported_user = MatchUserSerializer(read_only=True)
    reported_user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        source='reported_user'
    )
    match_id = serializers.PrimaryKeyRelatedField(
        queryset=Match.objects.all(),
        write_only=True,
        source='match',
        required=False,
        allow_null=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)

    class Meta:
        model = ChatReport
        fields = ['id', 'reporter', 'reported_user', 'reported_user_id',
                  'match', 'match_id', 'report_type', 'report_type_display',
                  'description', 'evidence', 'status', 'status_display',
                  'admin_notes', 'action_taken', 'created_at', 'resolved_at']
        read_only_fields = ['reporter', 'status', 'admin_notes',
                            'action_taken', 'resolved_at']

    def validate(self, attrs):
        """Валидация жалобы"""
        request = self.context.get('request')
        reported_user = attrs.get('reported_user')

        # Нельзя жаловаться на себя
        if reported_user == request.user:
            raise serializers.ValidationError("Нельзя жаловаться на себя")

        # Проверяем, не подавал ли уже жалобу на этого пользователя
        if ChatReport.objects.filter(
                reporter=request.user,
                reported_user=reported_user,
                status__in=['pending', 'investigating']
        ).exists():
            raise serializers.ValidationError("Вы уже подали жалобу на этого пользователя")

        return attrs


class CreateMatchSerializer(serializers.Serializer):
    """Сериализатор для создания мэтча"""
    user_id = serializers.IntegerField(required=True)
    match_type = serializers.ChoiceField(
        choices=Match._meta.get_field('match_type').choices,
        default='mutual_like'
    )

    def validate_user_id(self, value):
        """Валидация ID пользователя"""
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")

        # Нельзя создать мэтч с собой
        if user == self.context['request'].user:
            raise serializers.ValidationError("Нельзя создать мэтч с собой")

        return value

    def validate(self, attrs):
        """Валидация мэтча"""
        request = self.context.get('request')
        user_id = attrs.get('user_id')

        # Проверяем, существует ли уже мэтч
        if Match.objects.filter(
                (models.Q(user_1=request.user, user_2_id=user_id) |
                 models.Q(user_1_id=user_id, user_2=request.user))
        ).exists():
            raise serializers.ValidationError("Мэтч уже существует")

        # Проверяем блокировки
        if ChatBlock.objects.filter(
                models.Q(blocker=request.user, blocked_id=user_id) |
                models.Q(blocker_id=user_id, blocked=request.user)
        ).exists():
            raise serializers.ValidationError("Один из пользователей заблокирован")

        return attrs


class TypingIndicatorSerializer(serializers.Serializer):
    """Сериализатор индикатора набора"""
    match_id = serializers.IntegerField(required=True)
    is_typing = serializers.BooleanField(required=True)