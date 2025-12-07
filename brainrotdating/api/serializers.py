# api/serializers.py - ЗАМЕНИТЬ ВЕСЬ ФАЙЛ на:
from rest_framework import serializers
from characters.models import BrainRotCharacter, CharacterTrait
from .models import Question, AnswerOption, TestResult, Swipe, CompatibilityMatrix
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.core.validators import EmailValidator
from datetime import date
import re

User = get_user_model()


# === СЕРИАЛИЗАТОРЫ BRAINROT ТЕСТА ===

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


class BrainRotTestQuestionSerializer(serializers.ModelSerializer):
    """Сериализатор для вопросов BrainRot теста"""
    options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'options']

    def get_options(self, obj):
        options = obj.options.all().order_by('order')
        return BrainRotTestAnswerSerializer(options, many=True).data


class BrainRotTestAnswerSerializer(serializers.ModelSerializer):
    """Сериализатор для ответов BrainRot теста"""

    class Meta:
        model = AnswerOption
        fields = ['id', 'text', 'letter']


class BrainRotTestSubmitSerializer(serializers.Serializer):
    """Сериализатор для отправки ответов BrainRot теста"""
    answers = serializers.ListField(
        child=serializers.DictField(),
        help_text="Список ответов вида [{'question_id': 1, 'answer_id': 3}, ...]"
    )

    def validate(self, data):
        answers = data.get('answers', [])
        if len(answers) != 15:
            raise serializers.ValidationError(
                f"Требуется 15 ответов, получено {len(answers)}"
            )

        # Проверяем уникальность вопросов
        question_ids = [answer.get('question_id') for answer in answers]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError("Дублируются ответы на один вопрос")

        return data


class BrainRotTestResultSerializer(serializers.ModelSerializer):
    """Сериализатор результата BrainRot теста"""
    character = BrainRotCharacterSerializer(read_only=True)
    match_percentage = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = TestResult
        fields = ['character', 'scores', 'completed_at',
                  'match_percentage', 'description']

    def get_match_percentage(self, obj):
        """Рассчитывает процент совпадения"""
        if not obj.scores:
            return 0

        max_score = max(obj.scores.values())
        total = sum(obj.scores.values())
        return round((max_score / total) * 100, 1) if total > 0 else 0

    def get_description(self, obj):
        """Генерирует описание результата"""
        from .utils.brainrot_test_logic import generate_result_description
        return generate_result_description(
            obj.character,
            obj.scores,
            self.get_match_percentage(obj)
        )


# === СЕРИАЛИЗАТОРЫ СВАЙПОВ И СОВМЕСТИМОСТИ ===

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


# === СЕРИАЛИЗАТОРЫ АУТЕНТИФИКАЦИИ (если они тут нужны) ===
# Если они в отдельном файле - удалить отсюда

# === ОПЦИОНАЛЬНО: если нужны здесь сериализаторы пользователя ===
class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля пользователя"""
    age = serializers.IntegerField(read_only=True)
    brainrot_character = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'birth_date', 'age', 'phone', 'city', 'bio',
                  'brainrot_character', 'date_joined', 'last_login']

    def get_brainrot_character(self, obj):
        if hasattr(obj, 'brainrot_test_result') and obj.brainrot_test_result.character:
            return BrainRotCharacterSerializer(obj.brainrot_test_result.character).data
        return None


# === СЕРИАЛИЗАТОРЫ АУТЕНТИФИКАЦИИ ===

class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации"""
    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(queryset=User.objects.all(), message="Пользователь с таким email уже существует"),
            EmailValidator(message="Введите корректный email адрес")
        ]
    )
    username = serializers.CharField(
        required=True,
        min_length=3,
        max_length=30,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Это имя пользователя уже занято")]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    # Дополнительные поля для профиля
    birth_date = serializers.DateField(required=True, write_only=True)
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    city = serializers.CharField(required=False, max_length=100, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2',
                  'first_name', 'last_name', 'birth_date', 'phone', 'city')
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
        }

    def validate_username(self, value):
        """Валидация имени пользователя"""
        import re
        if not re.match(r'^[a-zA-Z0-9_.]+$', value):
            raise serializers.ValidationError(
                "Имя пользователя может содержать только буквы, цифры, точку и подчеркивание"
            )
        if value.lower() in ['admin', 'root', 'superuser', 'moderator']:
            raise serializers.ValidationError("Это имя пользователя запрещено")
        return value

    def validate_birth_date(self, value):
        """Валидация даты рождения"""
        from datetime import date
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

        if age < 18:
            raise serializers.ValidationError("Вы должны быть старше 18 лет")
        if value > today:
            raise serializers.ValidationError("Дата рождения не может быть в будущем")

        return value

    def validate(self, attrs):
        """Валидация паролей"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})

        password = attrs['password']
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Пароль должен быть не менее 8 символов"})
        if not any(char.isdigit() for char in password):
            raise serializers.ValidationError({"password": "Пароль должен содержать хотя бы одну цифру"})
        if not any(char.isalpha() for char in password):
            raise serializers.ValidationError({"password": "Пароль должен содержать хотя бы одну букву"})

        return attrs

    def create(self, validated_data):
        """Создание пользователя"""
        password2 = validated_data.pop('password2')
        password = validated_data.pop('password')

        birth_date = validated_data.pop('birth_date')
        phone = validated_data.pop('phone', '')
        city = validated_data.pop('city', '')

        user = User.objects.create(
            **validated_data,
            birth_date=birth_date,
            phone=phone,
            city=city
        )

        user.set_password(password)
        user.save()

        # Автоматически назначаем возрастную категорию
        if hasattr(user, 'assign_age_category'):
            user.assign_age_category()

        return user


class LoginSerializer(serializers.Serializer):
    """Сериализатор для входа"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Позволяем вход по email или username
        if '@' in username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                raise serializers.ValidationError({"username": "Пользователь с таким email не найден"})
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError({"username": "Пользователь с таким именем не найден"})

        # Проверяем пароль
        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Неверный пароль"})

        # Проверяем активность пользователя
        if not user.is_active:
            raise serializers.ValidationError({"username": "Аккаунт деактивирован"})

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Старый пароль неверен")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Новые пароли не совпадают"})
        return attrs


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления профиля"""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'city', 'bio')

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Этот email уже используется другим пользователем")
        return value