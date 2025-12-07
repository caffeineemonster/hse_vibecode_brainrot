# api/views.py
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
import random
import json

from characters.models import BrainRotCharacter
from .models import Question, AnswerOption, TestResult, Swipe, CompatibilityMatrix
from .serializers import (
    BrainRotCharacterSerializer, QuestionSerializer,
    TestSubmissionSerializer, TestResultSerializer,
    SwipeSerializer, CompatibilitySerializer,
    CharacterMatchSerializer
)


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
        ).order_by('-popularity_score', '?')  # Случайный порядок с учетом популярности

        # Фильтрация по категории (опционально)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """Рекомендованные персонажи на основе совместимости"""
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

            serializer = self.get_serializer(characters, many=True)
            return Response(serializer.data)

        return Response([])


class QuestionListView(generics.ListAPIView):
    """Список вопросов для теста"""
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]  # Можно проходить тест без регистрации

    def get_queryset(self):
        return Question.objects.filter(is_active=True).order_by('order')


class TestSubmitView(APIView):
    """Отправка ответов теста и получение результата"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TestSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        answers = serializer.validated_data['answers']

        # Алгоритм определения персонажа
        result = self.calculate_character(answers)

        # Сохраняем результат
        test_result, created = TestResult.objects.update_or_create(
            user=user,
            defaults={
                'character': result['character'],
                'score': result['scores']
            }
        )

        # Обновляем профиль пользователя
        if hasattr(user, 'brainrot_profile'):
            user.brainrot_profile.main_character = result['character']
            user.brainrot_profile.save()

        # Возвращаем результат
        result_serializer = TestResultSerializer(test_result)
        return Response({
            'result': result_serializer.data,
            'match_score': result['match_score'],
            'reasons': result['reasons']
        })

    def calculate_character(self, answers):
        """Алгоритм определения персонажа по ответам"""
        # 1. Собираем все персонажи
        characters = BrainRotCharacter.objects.filter(is_active=True)

        # 2. Инициализируем счетчики
        scores = {char.id: 0 for char in characters}

        # 3. Обрабатываем каждый ответ
        for answer_data in answers:
            question_id = answer_data.get('question_id')
            answer_id = answer_data.get('answer_id')

            try:
                answer_option = AnswerOption.objects.get(
                    id=answer_id,
                    question_id=question_id
                )

                # Получаем веса из JSON поля value
                weights = answer_option.value

                # Добавляем баллы персонажам
                for char_id, weight in weights.items():
                    if int(char_id) in scores:
                        scores[int(char_id)] += weight
            except AnswerOption.DoesNotExist:
                continue

        # 4. Находим персонажа с максимальным баллом
        best_char_id = max(scores, key=scores.get)
        best_character = BrainRotCharacter.objects.get(id=best_char_id)
        max_score = scores[best_char_id]

        # 5. Нормализуем баллы (0-100)
        total_possible_score = len(answers) * 10  # Максимум 10 баллов за вопрос
        match_score = (max_score / total_possible_score) * 100 if total_possible_score > 0 else 0

        # 6. Формируем причины выбора
        reasons = self.generate_reasons(best_character, scores)

        return {
            'character': best_character,
            'scores': scores,
            'match_score': match_score,
            'reasons': reasons
        }

    def generate_reasons(self, character, scores):
        """Генерация причин почему подошел этот персонаж"""
        reasons = []

        # Причина 1: Высокий общий балл
        char_score = scores[character.id]
        max_possible = max(scores.values())

        if char_score / max_possible > 0.8:
            reasons.append("Идеальное совпадение по большинству параметров")
        elif char_score / max_possible > 0.6:
            reasons.append("Хорошее совпадение по ключевым характеристикам")

        # Причина 2: Уникальные признаки персонажа
        traits = character.traits.all()[:2]
        for trait in traits:
            reasons.append(f"Ваше поведение схоже с '{trait.name}'")

        # Причина 3: Категория персонажа
        category_map = {
            'streamer': "Вы активны и любите внимание",
            'meme': "У вас отличное чувство юмора",
            'game': "Вы стратег и любите вызовы",
            'music': "Вы творческая личность",
        }

        if character.category in category_map:
            reasons.append(category_map[character.category])

        return reasons[:3]  # Возвращаем не более 3 причин


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
            return 1.0  # Персонаж совместим сам с собой

        # Базовый алгоритм совместимости
        score = 0.5  # Стартовый балл

        # 1. Совпадение категории (+0.3)
        if char1.category == char2.category:
            score += 0.3

        # 2. Совпадение признаков
        char1_traits = set(char1.traits.values_list('name', flat=True))
        char2_traits = set(char2.traits.values_list('name', flat=True))
        common_traits = char1_traits.intersection(char2_traits)

        if common_traits:
            score += len(common_traits) * 0.05

        # 3. Популярность (чем популярнее оба, тем выше совместимость)
        pop_factor = (char1.popularity_score + char2.popularity_score) / 2000
        score += min(pop_factor, 0.2)

        # Ограничиваем от 0.0 до 1.0
        return max(0.0, min(1.0, score))

    def generate_compatibility_description(self, char1, char2, score):
        """Генерация описания совместимости"""
        if score >= 0.8:
            return f"{char1.name} и {char2.name} - идеальный дуэт! Их энергии дополняют друг друга."
        elif score >= 0.6:
            return f"{char1.name} и {char2.name} хорошо ладят. У них есть общие интересы."
        elif score >= 0.4:
            return f"{char1.name} и {char2.name} могут найти общий язык, но иногда будут недопонимания."
        else:
            return f"{char1.name} и {char2.name} - полные противоположности. Это может быть интересно!"

    def generate_tags(self, char1, char2, score):
        """Генерация тегов совместимости"""
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


class SwipeViewSet(viewsets.ModelViewSet):
    """Управление свайпами"""
    serializer_class = SwipeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Swipe.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика свайпов пользователя"""
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
        """Определение самой лайкаемой категории"""
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
            common_likes__gte=1  # Хотя бы один общий лайк
        ).order_by('-common_likes')[:10]

        # Формируем ответ
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
        """Расчет совместимости между пользователями"""
        score = 0.5

        # 1. Возрастная категория
        if (hasattr(user1, 'age_category') and hasattr(user2, 'age_category') and
                user1.age_category == user2.age_category):
            score += 0.2

        # 2. BrainRot персонажи
        if (hasattr(user1, 'brainrot_profile') and hasattr(user2, 'brainrot_profile') and
                user1.brainrot_profile.main_character and user2.brainrot_profile.main_character):

            # Используем существующую матрицу совместимости
            compatibility = CompatibilityMatrix.objects.filter(
                Q(character_1=user1.brainrot_profile.main_character,
                  character_2=user2.brainrot_profile.main_character) |
                Q(character_1=user2.brainrot_profile.main_character,
                  character_2=user1.brainrot_profile.main_character)
            ).first()

            if compatibility:
                score += compatibility.score * 0.3

        return min(score, 1.0)


# api/views.py - добавь эти классы

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
        """Определение самой лайкаемой категории"""
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


# А в CharacterListView убери декоратор @action
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
        ).order_by('-popularity_score', '?')  # Случайный порядок с учетом популярности

        # Фильтрация по категории (опционально)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        return queryset


# И в SwipeViewSet убери декоратор @action
class SwipeViewSet(viewsets.ModelViewSet):
    """Управление свайпами"""
    serializer_class = SwipeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Swipe.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)