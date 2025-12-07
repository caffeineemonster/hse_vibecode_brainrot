# api/views_profile.py (создай новый файл)
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from characters.models import BrainRotCharacter, UserCharacterProfile
from api.models import Swipe, TestResult
from .serializers import UserProfileSerializer

User = get_user_model()


class UserStatsView(APIView):
    """Статистика пользователя"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Статистика по свайпам
        swipes_stats = Swipe.objects.filter(user=user).aggregate(
            total=Count('id'),
            likes=Count('id', filter=Q(swipe_type__in=['like', 'super_like'])),
            super_likes=Count('id', filter=Q(swipe_type='super_like')),
            dislikes=Count('id', filter=Q(swipe_type='dislike'))
        )

        # Взаимные лайки
        mutual_likes = Swipe.objects.filter(
            character__swipes__user=user,
            character__swipes__swipe_type__in=['like', 'super_like'],
            swipe_type__in=['like', 'super_like']
        ).exclude(
            character__swipes__user=user
        ).count()

        # Статистика по персонажу
        character_stats = {}
        if hasattr(user, 'brainrot_profile') and user.brainrot_profile.main_character:
            character = user.brainrot_profile.main_character
            character_stats = {
                'name': character.name,
                'level': user.brainrot_profile.character_level,
                'xp': user.brainrot_profile.xp_points,
                'xp_to_next_level': 100 - (user.brainrot_profile.xp_points % 100),
                'traits_count': user.all_traits.count() if hasattr(user, 'all_traits') else 0,
            }

        # Результат теста
        test_result = None
        if hasattr(user, 'test_result'):
            test_result = {
                'character': user.test_result.character.name if user.test_result.character else None,
                'completed_at': user.test_result.completed_at,
            }

        return Response({
            'swipes': swipes_stats,
            'mutual_likes': mutual_likes,
            'character': character_stats,
            'test_result': test_result,
            'account_age_days': (timezone.now() - user.date_joined).days,
        })


class UserMatchesView(generics.ListAPIView):
    """Список взаимных лайков (мэтчи)"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        user = self.request.user

        # Получаем персонажей, которых пользователь лайкнул
        user_liked_characters = Swipe.objects.filter(
            user=user,
            swipe_type__in=['like', 'super_like']
        ).values_list('character', flat=True)

        # Находим пользователей, которые тоже лайкнули этих персонажей
        # и которых пользователь лайкнул
        matching_users = User.objects.filter(
            # Их лайки на персонажей, которых лайкнул текущий пользователь
            swipes__character__in=user_liked_characters,
            swipes__swipe_type__in=['like', 'super_like'],
            # И текущий пользователь лайкнул их персонажей
            brainrot_profile__user_profiles__swipes__user=user,
            brainrot_profile__user_profiles__swipes__swipe_type__in=['like', 'super_like']
        ).exclude(id=user.id).distinct()

        return matching_users

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Дополнительная информация о мэтчах
        matches = []
        for match_user in queryset:
            # Общие лайки
            common_likes = Swipe.objects.filter(
                user=user,
                swipe_type__in=['like', 'super_like'],
                character__swipes__user=match_user,
                character__swipes__swipe_type__in=['like', 'super_like']
            ).count()

            matches.append({
                'user': UserProfileSerializer(match_user).data,
                'common_likes': common_likes,
                'compatibility_score': self.calculate_compatibility(request.user, match_user),
            })

        return Response(matches)

    def calculate_compatibility(self, user1, user2):
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
            from api.models import CompatibilityMatrix
            compatibility = CompatibilityMatrix.objects.filter(
                Q(character_1=user1.brainrot_profile.main_character,
                  character_2=user2.brainrot_profile.main_character) |
                Q(character_1=user2.brainrot_profile.main_character,
                  character_2=user1.brainrot_profile.main_character)
            ).first()

            if compatibility:
                score += compatibility.score * 0.3

        # 3. Общие интересы (по свайпам)
        common_characters = Swipe.objects.filter(
            user=user1,
            swipe_type__in=['like', 'super_like'],
            character__in=Swipe.objects.filter(
                user=user2,
                swipe_type__in=['like', 'super_like']
            ).values_list('character', flat=True)
        ).count()

        if common_characters > 0:
            score += min(common_characters * 0.1, 0.2)

        return round(min(score, 1.0), 2)


class UserActivityView(APIView):
    """Активность пользователя"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Последние свайпы
        recent_swipes = Swipe.objects.filter(user=user).order_by('-timestamp')[:10]

        # Рекомендации на основе активности
        recommendations = self.get_recommendations(user)

        return Response({
            'recent_activity': [
                {
                    'type': 'swipe',
                    'character': {
                        'id': swipe.character.id,
                        'name': swipe.character.name,
                        'category': swipe.character.get_category_display(),
                    },
                    'action': swipe.get_swipe_type_display(),
                    'timestamp': swipe.timestamp,
                }
                for swipe in recent_swipes
            ],
            'recommendations': recommendations,
        })

    def get_recommendations(self, user):
        """Получение рекомендаций на основе активности"""
        recommendations = []

        # 1. Персонажи из категорий, которые пользователь часто лайкает
        from django.db.models import Count
        liked_categories = Swipe.objects.filter(
            user=user,
            swipe_type__in=['like', 'super_like']
        ).values('character__category').annotate(
            count=Count('id')
        ).order_by('-count')[:2]

        for category in liked_categories:
            characters = BrainRotCharacter.objects.filter(
                category=category['character__category'],
                is_active=True
            ).exclude(
                id__in=Swipe.objects.filter(user=user).values_list('character', flat=True)
            )[:3]

            for character in characters:
                recommendations.append({
                    'type': 'category_based',
                    'character': {
                        'id': character.id,
                        'name': character.name,
                        'category': character.get_category_display(),
                    },
                    'reason': f'Вам нравятся персонажи категории "{character.get_category_display()}"',
                })

        return recommendations[:5]  # Не более 5 рекомендаций