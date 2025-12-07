# characters/models.py
from django.db import models


# Модель 1: BrainRot персонаж
class BrainRotCharacter(models.Model):
    """Базовый персонаж BrainRot"""
    CATEGORY_CHOICES = [
        ('streamer', 'Стример/Блогер'),
        ('meme', 'Мемный персонаж'),
        ('game', 'Игровой персонаж'),
        ('movie', 'Кино/Сериал'),
        ('music', 'Музыкальный'),
        ('internet', 'Интернет-персонаж'),
        ('other', 'Другое'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Название персонажа")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-идентификатор")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Категория")
    description = models.TextField(verbose_name="Описание персонажа")
    origin = models.CharField(max_length=200, blank=True, verbose_name="Происхождение")
    year_emerged = models.IntegerField(null=True, blank=True, verbose_name="Год появления")
    image = models.ImageField(upload_to='brainrot_characters/', blank=True, null=True, verbose_name="Изображение")
    iconic_phrase = models.CharField(max_length=200, blank=True, verbose_name="Культовая фраза")
    popularity_score = models.IntegerField(default=0, verbose_name="Популярность")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "BrainRot персонаж"
        verbose_name_plural = "BrainRot персонажи"
        ordering = ['-popularity_score', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


# Модель 2: Признак персонажа
class CharacterTrait(models.Model):
    """Признак/характеристика персонажа"""
    TRAIT_TYPE_CHOICES = [
        ('behavior', 'Поведение'),
        ('speech', 'Речь'),
        ('appearance', 'Внешность'),
        ('habit', 'Привычка'),
        ('reaction', 'Реакция'),
        ('preference', 'Предпочтение'),
        ('skill', 'Навык'),
        ('personality', 'Черта характера'),
    ]

    name = models.CharField(max_length=100, verbose_name="Название признака")
    trait_type = models.CharField(max_length=20, choices=TRAIT_TYPE_CHOICES, verbose_name="Тип признака")
    description = models.TextField(verbose_name="Описание признака")
    character = models.ForeignKey(
        BrainRotCharacter,
        on_delete=models.CASCADE,
        related_name='traits',
        null=True,
        blank=True,
        verbose_name="Персонаж"
    )
    is_global = models.BooleanField(default=False, verbose_name="Глобальный признак")
    min_value = models.IntegerField(default=1, verbose_name="Минимальное значение")
    max_value = models.IntegerField(default=10, verbose_name="Максимальное значение")
    default_value = models.IntegerField(default=5, verbose_name="Значение по умолчанию")

    class Meta:
        verbose_name = "Признак персонажа"
        verbose_name_plural = "Признаки персонажей"
        ordering = ['trait_type', 'name']
        unique_together = ['name', 'character']

    def __str__(self):
        char_name = self.character.name if self.character else "Глобальный"
        return f"{self.name} ({char_name})"


# Модель 3: Профиль персонажа пользователя
class UserCharacterProfile(models.Model):
    """Профиль персонажа у конкретного пользователя"""
    user = models.OneToOneField(
        'users.CustomUser',  # Важно: указываем строкой, чтобы избежать циклических импортов
        on_delete=models.CASCADE,
        related_name='brainrot_profile',
        verbose_name="Пользователь"
    )
    main_character = models.ForeignKey(
        BrainRotCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        verbose_name="Основной BrainRot персонаж"
    )
    additional_characters = models.ManyToManyField(
        BrainRotCharacter,
        related_name='secondary_users',
        blank=True,
        verbose_name="Дополнительные персонажи"
    )
    custom_description = models.TextField(blank=True, verbose_name="Своё описание персонажа")
    is_public = models.BooleanField(default=True, verbose_name="Публичный профиль")
    show_in_search = models.BooleanField(default=True, verbose_name="Показывать в поиске")
    character_level = models.IntegerField(default=1, verbose_name="Уровень персонажа")
    xp_points = models.IntegerField(default=0, verbose_name="Очки опыта")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Профиль персонажа"
        verbose_name_plural = "Профили персонажей"

    def __str__(self):
        char_name = self.main_character.name if self.main_character else "Не выбран"
        return f"{self.user.username} - {char_name}"


# Модель 4: Значения признаков у пользователя
class UserTraitValue(models.Model):
    """Значение конкретного признака у пользователя"""
    user_profile = models.ForeignKey(
        UserCharacterProfile,
        on_delete=models.CASCADE,
        related_name='trait_values',
        verbose_name="Профиль пользователя"
    )
    trait = models.ForeignKey(
        CharacterTrait,
        on_delete=models.CASCADE,
        related_name='user_values',
        verbose_name="Признак"
    )
    value = models.IntegerField(verbose_name="Значение", help_text="Интенсивность признака от 1 до 10")
    custom_note = models.TextField(blank=True, verbose_name="Примечание пользователя")
    is_active = models.BooleanField(default=True, verbose_name="Признак активен")
    last_used = models.DateTimeField(auto_now=True, verbose_name="Последнее использование")

    class Meta:
        verbose_name = "Значение признака"
        verbose_name_plural = "Значения признаков"
        unique_together = ['user_profile', 'trait']

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.trait.name}: {self.value}"


# Модель 5: Кастомные признаки пользователя
class CustomTrait(models.Model):
    """Кастомные признаки, созданные пользователем"""
    user_profile = models.ForeignKey(
        UserCharacterProfile,
        on_delete=models.CASCADE,
        related_name='custom_traits',
        verbose_name="Профиль пользователя"
    )
    name = models.CharField(max_length=100, verbose_name="Название признака")
    description = models.TextField(verbose_name="Описание")
    trait_type = models.CharField(
        max_length=20,
        choices=CharacterTrait.TRAIT_TYPE_CHOICES,
        verbose_name="Тип признака"
    )
    value = models.IntegerField(default=5, verbose_name="Значение")
    max_value = models.IntegerField(default=10, verbose_name="Максимальное значение")
    is_public = models.BooleanField(default=False, verbose_name="Публичный признак")
    likes_count = models.IntegerField(default=0, verbose_name="Лайки")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Кастомный признак"
        verbose_name_plural = "Кастомные признаки"

    def __str__(self):
        return f"{self.user_profile.user.username}: {self.name}"