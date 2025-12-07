# api/models.py
from django.db import models
from users.models import CustomUser
from characters.models import BrainRotCharacter


class Question(models.Model):
    """Вопрос для теста на персонажа"""
    CATEGORY_CHOICES = [
        ('behavior', 'Поведение'),
        ('preferences', 'Предпочтения'),
        ('personality', 'Личность'),
        ('values', 'Ценности'),
        ('humor', 'Чувство юмора'),
        ('communication', 'Общение'),
    ]

    text = models.TextField(verbose_name="Текст вопроса")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="Категория")
    order = models.IntegerField(default=0, verbose_name="Порядок вопроса")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    # Добавляем поля времени
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self):
        return f"{self.text[:50]}... [{self.get_category_display()}]"


class AnswerOption(models.Model):
    """Вариант ответа на вопрос"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200, verbose_name="Текст ответа")
    value = models.JSONField(verbose_name="Значение для алгоритма",
                             help_text="JSON с весами для персонажей")
    order = models.IntegerField(default=0, verbose_name="Порядок ответа")

    # Добавляем поля времени
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"

    def __str__(self):
        return f"{self.text[:30]}..."


class TestResult(models.Model):
    """Результат теста пользователя"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='test_result')
    character = models.ForeignKey(BrainRotCharacter, on_delete=models.SET_NULL,
                                  null=True, blank=True, verbose_name="Результат")
    score = models.JSONField(verbose_name="Баллы по персонажам",
                             help_text="JSON с баллами для каждого персонажа")

    # Добавляем поля времени
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="Завершен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        verbose_name = "Результат теста"
        verbose_name_plural = "Результаты тестов"

    def __str__(self):
        char_name = self.character.name if self.character else "Не определен"
        return f"{self.user.username} - {char_name}"


class Swipe(models.Model):
    """Свайп пользователя"""
    SWIPE_CHOICES = [
        ('like', '❤️ Лайк'),
        ('dislike', '👎 Дизлайк'),
        ('super_like', '⭐ Суперлайк'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='swipes')
    character = models.ForeignKey(BrainRotCharacter, on_delete=models.CASCADE, related_name='swipes')
    swipe_type = models.CharField(max_length=20, choices=SWIPE_CHOICES, verbose_name="Тип свайпа")

    # Добавляем поля времени
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        unique_together = ['user', 'character']
        ordering = ['-timestamp']
        verbose_name = "Свайп"
        verbose_name_plural = "Свайпы"

    def __str__(self):
        return f"{self.user.username} → {self.character.name} [{self.swipe_type}]"


class CompatibilityMatrix(models.Model):
    """Матрица совместимости персонажей"""
    character_1 = models.ForeignKey(BrainRotCharacter, on_delete=models.CASCADE,
                                    related_name='compatibility_as_first')
    character_2 = models.ForeignKey(BrainRotCharacter, on_delete=models.CASCADE,
                                    related_name='compatibility_as_second')
    score = models.FloatField(verbose_name="Совместимость",
                              help_text="От 0.0 до 1.0")
    description = models.TextField(blank=True, verbose_name="Описание совместимости")
    tags = models.JSONField(default=list, blank=True,
                            verbose_name="Теги совместимости")

    # Добавляем поля времени
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        unique_together = ['character_1', 'character_2']
        verbose_name = "Совместимость"
        verbose_name_plural = "Матрица совместимости"

    def __str__(self):
        return f"{self.character_1.name} + {self.character_2.name} = {self.score:.2f}"