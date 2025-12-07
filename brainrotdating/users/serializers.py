# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, AgeCategory


# Сериализатор для возрастной категории
class AgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeCategory
        fields = ['id', 'name', 'generation', 'subcategory',
                  'min_age', 'max_age', 'description']


# Базовый сериализатор пользователя
class UserSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    age_category = AgeCategorySerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'birth_date', 'age', 'age_category', 'phone', 'city', 'bio',
                  'date_joined', 'last_login']
        read_only_fields = ['date_joined', 'last_login']


# Сериализатор для регистрации
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password2',
                  'first_name', 'last_name', 'birth_date', 'phone', 'city']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            birth_date=validated_data.get('birth_date'),
            phone=validated_data.get('phone', ''),
            city=validated_data.get('city', '')
        )
        return user


# Сериализатор для обновления профиля
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email',
                  'birth_date', 'phone', 'city', 'bio']

    def update(self, instance, validated_data):
        # Обновляем основные поля
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.birth_date = validated_data.get('birth_date', instance.birth_date)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.city = validated_data.get('city', instance.city)
        instance.bio = validated_data.get('bio', instance.bio)

        instance.save()

        # Автоматически назначаем возрастную категорию если изменилась дата рождения
        if 'birth_date' in validated_data:
            instance.assign_age_category()

        return instance


# Сериализатор для смены пароля
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        user = self.context['request'].user

        # Проверяем старый пароль
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({"old_password": "Неверный пароль"})

        # Проверяем совпадение новых паролей
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Пароли не совпадают"})

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


# Профиль пользователя с дополнительной информацией
class UserProfileSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    age_category = AgeCategorySerializer(read_only=True)
    brainrot_character = serializers.SerializerMethodField()
    all_traits = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'birth_date', 'age', 'age_category', 'phone', 'city', 'bio',
                  'brainrot_character', 'all_traits', 'date_joined', 'last_login']
        read_only_fields = fields

    def get_brainrot_character(self, obj):
        character = obj.brainrot_character
        if character:
            return {
                'id': character.id,
                'name': character.name,
                'level': character.level,
                'character_type': character.character_type
            }
        return None

    def get_all_traits(self, obj):
        return obj.all_traits if hasattr(obj, 'brainrot_profile') else []


# Лёгкий сериализатор (для списков и отношений)
class UserBriefSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'age', 'city']


# Сериализатор для логина
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )