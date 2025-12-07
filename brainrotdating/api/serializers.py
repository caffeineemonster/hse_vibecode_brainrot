# api/serializers.py
from rest_framework import serializers
from characters.models import BrainRotCharacter, CharacterTrait
from .models import Question, AnswerOption, TestResult, Swipe, CompatibilityMatrix


class BrainRotCharacterSerializer(serializers.ModelSerializer):
    """Сериализатор для персонажей в свайпере"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    traits = serializers.SerializerMethodField()

    class Meta:
        model = BrainRotCharacter
        fields = ['id', 'name', 'slug', 'category', 'category_display',
                  'description', 'image', 'iconic_phrase', 'traits',
                  'popularity_score']
        read_only_fields = ['traits', 'popularity_score']

    def get_traits(self, obj):
        """Получить 3 основных признака персонажа"""
        traits = obj.traits.all()[:3]
        return [{'name': t.name, 'type': t.get_trait_type_display()} for t in traits]


class QuestionSerializer(serializers.ModelSerializer):
    """Сериализатор для вопросов с вариантами ответов"""
    options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'category', 'options']

    def get_options(self, obj):
        options = obj.options.all()
        return AnswerOptionSerializer(options, many=True).data


class AnswerOptionSerializer(serializers.ModelSerializer):
    """Сериализатор для вариантов ответов"""

    class Meta:
        model = AnswerOption
        fields = ['id', 'text', 'value']


class TestSubmissionSerializer(serializers.Serializer):
    """Сериализатор для отправки ответов теста"""
    answers = serializers.ListField(
        child=serializers.DictField(),
        help_text="Список ответов вида [{'question_id': 1, 'answer_id': 3}, ...]"
    )

    def validate(self, data):
        """Валидация ответов"""
        answers = data.get('answers', [])
        if not answers:
            raise serializers.ValidationError("Список ответов не может быть пустым")

        # Проверяем, что все вопросы уникальны
        question_ids = [answer.get('question_id') for answer in answers]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError("Дублируются ответы на один вопрос")

        return data


class TestResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результата теста"""
    character = BrainRotCharacterSerializer(read_only=True)

    class Meta:
        model = TestResult
        fields = ['character', 'score', 'completed_at']


class SwipeSerializer(serializers.ModelSerializer):
    """Сериализатор для свайпов"""
    character = BrainRotCharacterSerializer(read_only=True)
    character_id = serializers.PrimaryKeyRelatedField(
        queryset=BrainRotCharacter.objects.all(),
        write_only=True,
        source='character'
    )

    class Meta:
        model = Swipe
        fields = ['id', 'character', 'character_id', 'swipe_type', 'timestamp']

    def create(self, validated_data):
        """Создание свайпа с проверкой на существование"""
        user = self.context['request'].user
        character = validated_data['character']
        swipe_type = validated_data['swipe_type']

        # Обновляем существующий свайп или создаем новый
        swipe, created = Swipe.objects.update_or_create(
            user=user,
            character=character,
            defaults={'swipe_type': swipe_type}
        )

        # Обновляем популярность персонажа
        if swipe_type == 'like':
            character.popularity_score += 1
        elif swipe_type == 'super_like':
            character.popularity_score += 3
        elif swipe_type == 'dislike':
            character.popularity_score -= 1
        character.save()

        return swipe


class CompatibilitySerializer(serializers.ModelSerializer):
    """Сериализатор для совместимости"""
    character_1 = BrainRotCharacterSerializer(read_only=True)
    character_2 = BrainRotCharacterSerializer(read_only=True)

    class Meta:
        model = CompatibilityMatrix
        fields = ['character_1', 'character_2', 'score', 'description', 'tags']


class CharacterMatchSerializer(serializers.Serializer):
    """Сериализатор для подбора персонажа"""
    character = BrainRotCharacterSerializer()
    match_score = serializers.FloatField(min_value=0.0, max_value=100.0)
    reasons = serializers.ListField(child=serializers.CharField())