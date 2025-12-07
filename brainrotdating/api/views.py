# api/views.py - ЗАМЕНИТЬ ВЕСЬ ФАЙЛ на:
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
import random

from characters.models import BrainRotCharacter
from .models import Question, AnswerOption, TestResult, Swipe, CompatibilityMatrix
from .serializers import (
    BrainRotCharacterSerializer,
    BrainRotTestQuestionSerializer,
    BrainRotTestSubmitSerializer,
    BrainRotTestResultSerializer,
    SwipeSerializer,
    CompatibilitySerializer,
    CharacterMatchSerializer
)
from .utils.brainrot_test_logic import (
    calculate_brainrot_result,
    get_brainrot_test_questions,
    BRAINROT_CHARACTER_MAP,
    TIE_CHARACTERS
)


# === BRAINROT ТЕСТ ===

class BrainRotTestQuestionsView(generics.ListAPIView):
    """Получение вопросов для BrainRot теста"""
    serializer_class = BrainRotTestQuestionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_brainrot_test_questions()


class BrainRotTestSubmitView(APIView):
    """Отправка ответов BrainRot теста"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BrainRotTestSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        answers = serializer.validated_data['answers']

        # Рассчитываем результат
        result = calculate_brainrot_result(answers)

        if not result:
            return Response(
                {'error': 'Не удалось рассчитать результат'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Сохраняем результат теста
        test_result, created = TestResult.objects.update_or_create(
            user=user,
            defaults={
                'character': result['character'],
                'scores': result['scores']
            }
        )

        # Обновляем профиль пользователя
        if hasattr(user, 'brainrot_profile'):
            user.brainrot_profile.main_character = result['character']
            user.brainrot_profile.character_level = 1
            user.brainrot_profile.xp_points = 100  # Награда за прохождение теста
            user.brainrot_profile.save()

        # Сериализуем и возвращаем результат
        result_serializer = BrainRotTestResultSerializer(test_result)
        return Response({
            'success': True,
            'result': result_serializer.data,
            'message': '🎭 Тест пройден! Теперь ты часть BrainRot вселенной!'
        })


class BrainRotTestPreviewView(APIView):
    """Предпросмотр возможных результатов теста"""
    permission_classes = [AllowAny]

    def get(self, request):
        # Основные персонажи
        characters = []
        for letter, char_data in BRAINROT_CHARACTER_MAP.items():
            characters.append({
                'letter': letter,
                'name': char_data['name'],
                'description': char_data['description'],
                'category': char_data['category'],
                'iconic_phrase': char_data.get('iconic_phrase', '')
            })

        # Персонажи для ничьих
        tie_characters = []
        for tie_key, char_data in TIE_CHARACTERS.items():
            tie_characters.append({
                'combination': tie_key,
                'name': char_data['name'],
                'description': char_data['description'],
                'category': char_data['category'],
                'iconic_phrase': char_data.get('iconic_phrase', '')
            })

        return Response({
            'main_characters': characters,
            'tie_characters': tie_characters,
            'test_info': {
                'total_questions': 15,
                'type': 'brainrot_simple',
                'instructions': 'Выберите по одному ответу (A-F) на каждый вопрос. В конце система определит вашего BrainRot персонажа.'
            }
        })


# === СВАЙПЕР ===

class CharacterListView(generics.ListAPIView):
    """Список персонажей для свайпера"""
    serializer_class = BrainRotCharacterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Получаем ID персонажей, которых пользователь уже свайпал
        swiped_char_ids = Swipe.objects.filter(user=user).values_list('character_id', flat=True)

        # Исключаем уже свайпнутых, показываем только активных
        queryset = BrainRotCharacter.objects.filter(
            is_active=True
        ).exclude(
            id__in=swiped_char_ids
        ).order_by('-popularity_score', '?')

        # Фильтрация по категории (опционально)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        return queryset


class RecommendedCharactersView(APIView):
    """Рекомендованные персонажи на основе совместимости"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Получаем основной персонаж пользователя
        if hasattr(user, 'brainrot_profile') and user.brainrot_profile.main_character:
            main_character = user.brainrot_profile.main_character

            # Получаем персонажей с высокой совместимостью
            compatibilities = CompatibilityMatrix.objects.filter(
                Q(character_1=main_character) | Q(character_2=main_character)
            ).order_by('-score')[:10]

            # Собираем ID рекомендованных персонажей
            recommended_ids = []
            for comp in compatibilities:
                if comp.character_1 == main_character:
                    recommended_ids.append(comp.character_2_id)
                else:
                    recommended_ids.append(comp.character_1_id)

            # Получаем персонажей
            characters = BrainRotCharacter.objects.filter(
                id__in=recommended_ids,
                is_active=True
            )

            # Исключаем уже свайпнутых
            swiped_ids = Swipe.objects.filter(user=user).values_list('character_id', flat=True)
            characters = characters.exclude(id__in=swiped_ids)

            serializer = BrainRotCharacterSerializer(characters, many=True)
            return Response(serializer.data)

        return Response([])


# === СОВМЕСТИМОСТЬ ===

class CompatibilityView(APIView):
    """Получение совместимости двух персонажей"""
    permission_classes = [IsAuthenticated]

    def get(self, request, char1_id, char2_id):
        char1 = get_object_or_404(BrainRotCharacter, id=char1_id)
        char2 = get_object_or_404(BrainRotCharacter, id=char2_id)

        # Ищем совместимость в базе
        compatibility = CompatibilityMatrix.objects.filter(
            Q(character_1=char1, character_2=char2) |
            Q(character_1=char2, character_2=char1)
        ).first()

        if not compatibility:
            # Рассчитываем совместимость на лету
            score = self.calculate_compatibility(char1, char2)
            description = self.generate_compatibility_description(char1, char2, score)

            compatibility = CompatibilityMatrix.objects.create(
                character_1=char1,
                character_2=char2,
                score=score,
                description=description,
                tags=self.generate_tags(char1, char2, score)
            )

        serializer = CompatibilitySerializer(compatibility)
        return Response(serializer.data)

    def calculate_compatibility(self, char1, char2):
        """Расчет совместимости между персонажами"""
        if char1 == char2:
            return 1.0

        score = 0.5

        if char1.category == char2.category:
            score += 0.3

        char1_traits = set(char1.traits.values_list('name', flat=True))
        char2_traits = set(char2.traits.values_list('name', flat=True))
        common_traits = char1_traits.intersection(char2_traits)

        if common_traits:
            score += len(common_traits) * 0.05

        pop_factor = (char1.popularity_score + char2.popularity_score) / 2000
        score += min(pop_factor, 0.2)

        return max(0.0, min(1.0, score))

    def generate_compatibility_description(self, char1, char2, score):
        if score >= 0.8:
            return f"{char1.name} и {char2.name} - идеальный дуэт! Их энергии дополняют друг друга."
        elif score >= 0.6:
            return f"{char1.name} и {char2.name} хорошо ладят. У них есть общие интересы."
        elif score >= 0.4:
            return f"{char1.name} и {char2.name} могут найти общий язык, но иногда будут недопонимания."
        else:
            return f"{char1.name} и {char2.name} - полные противоположности. Это может быть интересно!"

    def generate_tags(self, char1, char2, score):
        tags = []
        if score >= 0.7:
            tags.append('high_compatibility')
            tags.append('recommended')
        elif score <= 0.3:
            tags.append('chaotic')
            tags.append('experimental')
        if char1.category == char2.category:
            tags.append('same_category')
        return tags


# === СВАЙПЫ ===

class SwipeViewSet(viewsets.ModelViewSet):
    """Управление свайпами"""
    serializer_class = SwipeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Swipe.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SwipeStatsView(APIView):
    """Статистика свайпов пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        stats = {
            'total_swipes': Swipe.objects.filter(user=user).count(),
            'likes': Swipe.objects.filter(user=user, swipe_type='like').count(),
            'dislikes': Swipe.objects.filter(user=user, swipe_type='dislike').count(),
            'super_likes': Swipe.objects.filter(user=user, swipe_type='super_like').count(),
            'most_liked_category': self.get_most_liked_category(user),
        }

        return Response(stats)

    def get_most_liked_category(self, user):
        from django.db.models import Count
        likes_by_category = Swipe.objects.filter(
            user=user,
            swipe_type__in=['like', 'super_like']
        ).values(
            'character__category'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        if likes_by_category:
            return likes_by_category[0]['character__category']
        return None


# === МЭТЧИ ===

class MatchSuggestionView(APIView):
    """Подбор потенциальных мэтчей на основе свайпов"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Получаем персонажей, которых пользователь лайкнул
        liked_characters = Swipe.objects.filter(
            user=user,
            swipe_type__in=['like', 'super_like']
        ).values_list('character', flat=True)

        if not liked_characters:
            return Response([])

        # Находим других пользователей, которые тоже лайкнули этих персонажей
        from django.db.models import Count
        from users.models import CustomUser

        potential_matches = CustomUser.objects.filter(
            swipes__character__in=liked_characters,
            swipes__swipe_type__in=['like', 'super_like']
        ).exclude(
            id=user.id
        ).annotate(
            common_likes=Count('swipes', filter=Q(
                swipes__character__in=liked_characters,
                swipes__swipe_type__in=['like', 'super_like']
            ))
        ).filter(
            common_likes__gte=1
        ).order_by('-common_likes')[:10]

        matches = []
        for match_user in potential_matches:
            matches.append({
                'user': {
                    'id': match_user.id,
                    'username': match_user.username,
                    'age': match_user.age if hasattr(match_user, 'age') else None,
                    'city': match_user.city,
                },
                'common_likes': match_user.common_likes,
                'compatibility': self.calculate_user_compatibility(user, match_user)
            })

        return Response(matches)

    def calculate_user_compatibility(self, user1, user2):
        score = 0.5

        if (hasattr(user1, 'age_category') and hasattr(user2, 'age_category') and
                user1.age_category == user2.age_category):
            score += 0.2

        if (hasattr(user1, 'brainrot_profile') and hasattr(user2, 'brainrot_profile') and
                user1.brainrot_profile.main_character and user2.brainrot_profile.main_character):

            compatibility = CompatibilityMatrix.objects.filter(
                Q(character_1=user1.brainrot_profile.main_character,
                  character_2=user2.brainrot_profile.main_character) |
                Q(character_1=user2.brainrot_profile.main_character,
                  character_2=user1.brainrot_profile.main_character)
            ).first()

            if compatibility:
                score += compatibility.score * 0.3

        return min(score, 1.0)