# chat/views.py
from rest_framework import viewsets, generics, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Max, Subquery, OuterRef
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from .models import (
    Match, Message, Reaction, ChatSettings,
    UserPresence, ChatBlock, ChatReport
)
from .serializers import (
    MatchSerializer, MessageSerializer, ReactionSerializer,
    ChatSettingsSerializer, UserPresenceSerializer,
    ChatBlockSerializer, ChatReportSerializer,
    CreateMatchSerializer, TypingIndicatorSerializer
)
from api.models import CompatibilityMatrix

User = get_user_model()


class MatchViewSet(viewsets.ModelViewSet):
    """ViewSet для мэтчей"""
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получить мэтчи текущего пользователя"""
        user = self.request.user
        return Match.objects.filter(
            Q(user_1=user) | Q(user_2=user)
        ).select_related(
            'user_1', 'user_2',
            'user_1__brainrot_profile__main_character',
            'user_2__brainrot_profile__main_character',
            'user_1__presence', 'user_2__presence',
            'user_1__age_category', 'user_2__age_category'
        ).prefetch_related(
            'messages'
        ).order_by('-last_message_at', '-created_at')

    def get_serializer_context(self):
        """Добавляем request в контекст"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['post'])
    def create_match(self, request):
        """Создание нового мэтча"""
        serializer = CreateMatchSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            match_type = serializer.validated_data['match_type']

            try:
                other_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Создаем мэтч
            match = Match.objects.create(
                user_1=request.user,
                user_2=other_user,
                match_type=match_type
            )

            # Рассчитываем совместимость если есть BrainRot персонажи
            if (hasattr(request.user, 'brainrot_profile') and
                    hasattr(other_user, 'brainrot_profile') and
                    request.user.brainrot_profile.main_character and
                    other_user.brainrot_profile.main_character):

                char1 = request.user.brainrot_profile.main_character
                char2 = other_user.brainrot_profile.main_character

                compatibility = CompatibilityMatrix.objects.filter(
                    Q(character_1=char1, character_2=char2) |
                    Q(character_1=char2, character_2=char1)
                ).first()

                if compatibility:
                    match.compatibility_score = compatibility.score
                    match.save()

            return Response(
                MatchSerializer(match, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Принять мэтч"""
        match = self.get_object()

        if match.user_2 != request.user:
            return Response(
                {"error": "Вы не можете принять этот мэтч"},
                status=status.HTTP_403_FORBIDDEN
            )

        match.status = 'accepted'
        match.save()

        return Response(
            MatchSerializer(match, context={'request': request}).data
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонить мэтч"""
        match = self.get_object()

        if match.user_2 != request.user:
            return Response(
                {"error": "Вы не можете отклонить этот мэтч"},
                status=status.HTTP_403_FORBIDDEN
            )

        match.status = 'rejected'
        match.save()

        return Response(
            {"message": "Мэтч отклонен"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Заблокировать чат"""
        match = self.get_object()
        other_user = match.get_other_user(request.user)

        # Создаем блокировку
        ChatBlock.objects.create(
            blocker=request.user,
            blocked=other_user,
            block_type='full',
            reason="Блокировка через мэтч"
        )

        # Деактивируем чат
        match.is_chat_active = False
        match.save()

        return Response(
            {"message": "Чат заблокирован"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Получить сообщения мэтча"""
        match = self.get_object()

        # Помечаем сообщения как прочитанные
        Message.objects.filter(
            match=match,
            read_at__isnull=True
        ).exclude(
            sender=request.user
        ).update(read_at=timezone.now())

        # Получаем сообщения
        messages = match.messages.filter(is_deleted=False).order_by('sent_at')
        page = self.paginate_queryset(messages)

        if page is not None:
            serializer = MessageSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(
            messages,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Получить ожидающие мэтчи"""
        pending_matches = Match.objects.filter(
            user_2=request.user,
            status='pending'
        ).select_related('user_1', 'user_1__brainrot_profile__main_character')

        serializer = self.get_serializer(pending_matches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Общее количество непрочитанных сообщений"""
        user_matches = Match.objects.filter(
            Q(user_1=request.user) | Q(user_2=request.user),
            status='accepted',
            is_chat_active=True
        )

        total_unread = 0
        for match in user_matches:
            total_unread += match.unread_count(request.user)

        return Response({"total_unread": total_unread})


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet для сообщений"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получить сообщения пользователя"""
        user = self.request.user

        # Сообщения в мэтчах пользователя
        user_matches = Match.objects.filter(
            Q(user_1=user) | Q(user_2=user),
            status='accepted',
            is_chat_active=True
        )

        return Message.objects.filter(
            match__in=user_matches,
            is_deleted=False
        ).select_related(
            'sender', 'match', 'brainrot_character'
        ).prefetch_related(
            'reactions'
        ).order_by('-sent_at')

    def perform_create(self, serializer):
        """Создание сообщения"""
        message = serializer.save()

        # Отправляем уведомление через WebSocket
        self.send_websocket_notification(message)

    def perform_update(self, serializer):
        """Обновление сообщения"""
        message = serializer.save()
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save()

    def perform_destroy(self, instance):
        """Мягкое удаление сообщения"""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()

    def send_websocket_notification(self, message):
        """Отправка уведомления через WebSocket"""
        # Здесь будет логика отправки через Django Channels
        pass

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Пометить сообщение как прочитанное"""
        message = self.get_object()

        # Проверяем, что пользователь получатель
        if message.match.get_other_user(message.sender) != request.user:
            return Response(
                {"error": "Вы не получатель этого сообщения"},
                status=status.HTTP_403_FORBIDDEN
            )

        message.read_at = timezone.now()
        message.save()

        return Response({"status": "Прочитано"})

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Добавить реакцию на сообщение"""
        message = self.get_object()
        reaction_type = request.data.get('reaction_type')

        if not reaction_type:
            return Response(
                {"error": "Укажите тип реакции"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создаем или обновляем реакцию
        reaction, created = Reaction.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'reaction_type': reaction_type}
        )

        serializer = ReactionSerializer(reaction)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def remove_reaction(self, request, pk=None):
        """Удалить реакцию"""
        message = self.get_object()

        Reaction.objects.filter(
            message=message,
            user=request.user
        ).delete()

        return Response({"status": "Реакция удалена"})


class ChatSettingsView(generics.RetrieveUpdateAPIView):
    """Настройки чата"""
    serializer_class = ChatSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Получить или создать настройки"""
        user = self.request.user
        settings, created = ChatSettings.objects.get_or_create(user=user)
        return settings


class UserPresenceViewSet(mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         viewsets.GenericViewSet):
    """ViewSet для онлайн статуса пользователя"""
    serializer_class = UserPresenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Получить или создать статус"""
        user = self.request.user
        presence, created = UserPresence.objects.get_or_create(user=user)
        return presence

    @action(detail=False, methods=['post'])
    def update_presence(self, request):
        """Обновить онлайн статус"""
        presence = self.get_object()

        # Обновляем активность
        presence.last_activity = timezone.now()

        # Обновляем статус если передан
        new_status = request.data.get('status')
        if new_status:
            presence.status = new_status

        # Обновляем текущий чат если передан
        match_id = request.data.get('current_chat')
        if match_id:
            try:
                match = Match.objects.get(id=match_id)
                presence.current_chat = match
            except Match.DoesNotExist:
                pass

        presence.save()

        serializer = self.get_serializer(presence)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def typing(self, request):
        """Обновить статус набора текста"""
        serializer = TypingIndicatorSerializer(data=request.data)
        if serializer.is_valid():
            match_id = serializer.validated_data['match_id']
            is_typing = serializer.validated_data['is_typing']

            try:
                match = Match.objects.get(id=match_id)
                presence = self.get_object()
                presence.is_typing = is_typing

                if is_typing:
                    presence.current_chat = match

                presence.save()

                # Отправляем уведомление через WebSocket
                self.send_typing_notification(match, is_typing)

                return Response({"status": "Статус обновлен"})
            except Match.DoesNotExist:
                return Response(
                    {"error": "Мэтч не найден"},
                    status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_typing_notification(self, match, is_typing):
        """Отправка уведомления о наборе текста"""
        pass  # Логика WebSocket

class ChatBlockViewSet(viewsets.ModelViewSet):
    """Блокировки пользователей"""
    serializer_class = ChatBlockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получить блокировки пользователя"""
        return ChatBlock.objects.filter(
            blocker=self.request.user
        ).select_related('blocked')

    def perform_create(self, serializer):
        """Создание блокировки"""
        block = serializer.save(blocker=self.request.user)

        # Деактивируем все активные мэтчи с заблокированным пользователем
        Match.objects.filter(
            Q(user_1=self.request.user, user_2=block.blocked) |
            Q(user_1=block.blocked, user_2=self.request.user),
            is_chat_active=True
        ).update(is_chat_active=False)


class ChatReportViewSet(viewsets.ModelViewSet):
    """Жалобы на пользователей"""
    serializer_class = ChatReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получить жалобы пользователя"""
        return ChatReport.objects.filter(
            reporter=self.request.user
        ).select_related('reported_user', 'match')

    def perform_create(self, serializer):
        """Создание жалобы"""
        serializer.save(reporter=self.request.user)


class OnlineUsersView(APIView):
    """Список онлайн пользователей"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Получить онлайн пользователей"""
        # Пользователи, активные за последние 5 минут
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)

        online_users = UserPresence.objects.filter(
            last_activity__gte=five_minutes_ago,
            status__in=['online', 'away', 'busy']
        ).exclude(
            user=request.user
        ).select_related('user').order_by('-last_activity')

        # Фильтруем по возрасту и городу если указаны
        min_age = request.query_params.get('min_age')
        max_age = request.query_params.get('max_age')
        city = request.query_params.get('city')

        filtered_users = []
        for presence in online_users:
            user = presence.user

            # Фильтр по возрасту
            if min_age and user.age and user.age < int(min_age):
                continue
            if max_age and user.age and user.age > int(max_age):
                continue

            # Фильтр по городу
            if city and user.city and city.lower() not in user.city.lower():
                continue

            filtered_users.append(presence)

        serializer = UserPresenceSerializer(
            filtered_users[:50],  # Ограничиваем 50 пользователями
            many=True
        )

        return Response({
            'count': len(filtered_users),
            'users': serializer.data
        })


class ChatSearchView(APIView):
    """Поиск в чатах"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Поиск сообщений и пользователей"""
        query = request.query_params.get('q', '').strip()
        if not query or len(query) < 2:
            return Response({"error": "Минимум 2 символа для поиска"})

        user = request.user

        # Поиск сообщений
        messages = Message.objects.filter(
            Q(match__user_1=user) | Q(match__user_2=user),
            content__icontains=query,
            is_deleted=False
        ).select_related('sender', 'match')[:20]

        # Поиск в мэтчах (по именам пользователей)
        matches = Match.objects.filter(
            Q(user_1=user) | Q(user_2=user),
            Q(user_1__username__icontains=query) |
            Q(user_1__first_name__icontains=query) |
            Q(user_1__last_name__icontains=query) |
            Q(user_2__username__icontains=query) |
            Q(user_2__first_name__icontains=query) |
            Q(user_2__last_name__icontains=query)
        )[:10]

        return Response({
            'messages': MessageSerializer(messages, many=True).data,
            'matches': MatchSerializer(matches, many=True, context={'request': request}).data,
            'query': query
        })