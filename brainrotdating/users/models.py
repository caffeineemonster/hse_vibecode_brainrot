# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date


# Модель 1: Возрастные категории
class AgeCategory(models.Model):
    """Модель для возрастных категорий/поколений"""
    GENERATION_CHOICES = [
        ('gen_z', 'Поколение Z (1997-2012)'),
        ('millennials', 'Миллениалы (1981-1996)'),
        ('gen_x', 'Поколение X (1965-1980)'),
        ('boomers_ii', 'Бумеры II (1955-1964)'),
        ('boomers_i', 'Бумеры I (1946-1954)'),
        ('silent', 'Молчаливое поколение (1928-1945)'),
    ]

    name = models.CharField(max_length=100, verbose_name="Название категории")
    generation = models.CharField(max_length=20, choices=GENERATION_CHOICES, verbose_name="Поколение")
    subcategory = models.CharField(max_length=50, verbose_name="Подкатегория",
                                   help_text="Например: Ранние Z, Поздние Z")

    min_age = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Минимальный возраст")
    max_age = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Максимальный возраст")
    birth_year_from = models.IntegerField(verbose_name="Год рождения от")
    birth_year_to = models.IntegerField(verbose_name="Год рождения до")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Возрастная категория"
        verbose_name_plural = "Возрастные категории"
        ordering = ['-birth_year_from']

    def __str__(self):
        return f"{self.name} ({self.min_age}-{self.max_age} лет)"


# Модель 2: Основной пользователь
class CustomUser(AbstractUser):
    """Модель пользователя с расширенными полями"""

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='customuser_set',  # ✅ Измени это
        related_query_name='customuser',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set',  # ✅ Измени это
        related_query_name='customuser',
    )

    # Поля для возраста и категорий
    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    age_category = models.ForeignKey(
        AgeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Возрастная категория",
        related_name='users'
    )

    # Дополнительные поля
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    city = models.CharField(max_length=100, blank=True, verbose_name="Город")
    bio = models.TextField(blank=True, verbose_name="О себе")

    # BrainRot персонаж будет доступен через OneToOne связь
    # brainrot_profile создастся автоматически через сигнал

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-date_joined']

    @property
    def age(self):
        """Вычисляет текущий возраст"""
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                    (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    @property
    def brainrot_character(self):
        """Основной BrainRot персонаж пользователя"""
        if hasattr(self, 'brainrot_profile'):
            return self.brainrot_profile.main_character
        return None

    @property
    def all_traits(self):
        """Все признаки пользователя (стандартные + кастомные)"""
        if not hasattr(self, 'brainrot_profile'):
            return []

        traits = []
        # Стандартные признаки
        for tv in self.brainrot_profile.trait_values.filter(is_active=True):
            traits.append({
                'type': 'standard',
                'name': tv.trait.name,
                'value': tv.value,
                'description': tv.trait.description,
                'trait_type': tv.trait.trait_type,
            })

        # Кастомные признаки
        for ct in self.brainrot_profile.custom_traits.all():
            traits.append({
                'type': 'custom',
                'name': ct.name,
                'value': ct.value,
                'description': ct.description,
                'trait_type': ct.trait_type,
            })

        return traits

    def create_brainrot_profile(self):
        """Создать профиль BrainRot, если его нет"""
        if not hasattr(self, 'brainrot_profile'):
            from characters.models import UserCharacterProfile
            UserCharacterProfile.objects.create(user=self)
            return True
        return False

    def assign_age_category(self):
        """Автоматически назначает возрастную категорию"""
        if not self.birth_date:
            return None

        age = self.age
        if age:
            # Ищем подходящую категорию
            category = AgeCategory.objects.filter(
                min_age__lte=age,
                max_age__gte=age
            ).first()
            self.age_category = category
            self.save()
            return category
        return None
