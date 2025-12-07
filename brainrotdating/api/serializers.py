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


# api/serializers.py (дополнение)
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.core.validators import EmailValidator
from datetime import date
import re

User = get_user_model()


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
        if not re.match(r'^[a-zA-Z0-9_.]+$', value):
            raise serializers.ValidationError(
                "Имя пользователя может содержать только буквы, цифры, точку и подчеркивание"
            )
        if value.lower() in ['admin', 'root', 'superuser', 'moderator']:
            raise serializers.ValidationError("Это имя пользователя запрещено")
        return value

    def validate_birth_date(self, value):
        """Валидация даты рождения"""
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

        # Проверяем сложность пароля
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
        # Убираем password2 из данных
        password2 = validated_data.pop('password2')
        password = validated_data.pop('password')

        # Извлекаем дополнительные поля
        birth_date = validated_data.pop('birth_date')
        phone = validated_data.pop('phone', '')
        city = validated_data.pop('city', '')

        # Создаем пользователя
        user = User.objects.create(
            **validated_data,
            birth_date=birth_date,
            phone=phone,
            city=city
        )

        # Устанавливаем пароль
        user.set_password(password)
        user.save()

        # Автоматически назначаем возрастную категорию
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


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля пользователя"""
    age = serializers.SerializerMethodField()
    age_category = serializers.SerializerMethodField()
    brainrot_character = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'birth_date', 'age', 'age_category', 'phone', 'city', 'bio',
                  'brainrot_character', 'date_joined', 'last_login')
        read_only_fields = ('id', 'date_joined', 'last_login')

    def get_age(self, obj):
        return obj.age

    def get_age_category(self, obj):
        if obj.age_category:
            return {
                'id': obj.age_category.id,
                'name': obj.age_category.name,
                'generation': obj.age_category.get_generation_display(),
                'subcategory': obj.age_category.subcategory,
            }
        return None

    def get_brainrot_character(self, obj):
        if hasattr(obj, 'brainrot_profile') and obj.brainrot_profile.main_character:
            return {
                'id': obj.brainrot_profile.main_character.id,
                'name': obj.brainrot_profile.main_character.name,
                'category': obj.brainrot_profile.main_character.get_category_display(),
            }
        return None


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