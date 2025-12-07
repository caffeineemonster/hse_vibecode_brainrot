# api/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Question, AnswerOption, TestResult, Swipe, CompatibilityMatrix


# ========== INLINE МОДЕЛИ ==========

class AnswerOptionInline(admin.TabularInline):
    """Inline вариантов ответов для вопросов"""
    model = AnswerOption
    extra = 1
    fields = ('text', 'value', 'order')
    ordering = ('order',)


# Убери SwipeInline или исправь его:
# Swipe НЕ связан с TestResult, поэтому inline не нужен
# Если хочешь оставить SwipeInline в TestResultAdmin, нужно изменить модель Swipe

# ========== ОСНОВНЫЕ МОДЕЛИ ==========

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Админка вопросов теста"""
    inlines = [AnswerOptionInline]

    list_display = ('text_preview', 'category_display', 'order',
                    'options_count', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('text',)
    list_editable = ('order', 'is_active')
    ordering = ('order', 'id')

    fieldsets = (
        ('Основная информация', {
            'fields': ('text', 'category', 'order', 'is_active')
        }),
    )

    actions = ['activate_questions', 'deactivate_questions', 'reorder_questions']

    def text_preview(self, obj):
        """Превью текста вопроса"""
        return f"{obj.text[:70]}..." if len(obj.text) > 70 else obj.text

    text_preview.short_description = 'Вопрос'

    def category_display(self, obj):
        """Отображение категории с цветом"""
        colors = {
            'behavior': '#FF6B6B',
            'preferences': '#4ECDC4',
            'personality': '#45B7D1',
            'values': '#96CEB4',
            'humor': '#FFEAA7',
            'communication': '#DDA0DD',
        }
        color = colors.get(obj.category, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px;">{}</span>',
            color, obj.get_category_display()
        )

    category_display.short_description = 'Категория'

    def options_count(self, obj):
        """Количество вариантов ответа"""
        return obj.options.count()

    options_count.short_description = '📝 Вариантов'

    def activate_questions(self, request, queryset):
        """Активировать выбранные вопросы"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} вопросов активировано')

    activate_questions.short_description = "✅ Активировать вопросы"

    def deactivate_questions(self, request, queryset):
        """Деактивировать выбранные вопросы"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} вопросов деактивировано')

    deactivate_questions.short_description = "❌ Деактивировать вопросы"

    def reorder_questions(self, request, queryset):
        """Перенумеровать порядок вопросов"""
        for index, question in enumerate(queryset.order_by('order', 'id'), start=1):
            question.order = index
            question.save()
        self.message_user(request, f'Порядок {queryset.count()} вопросов обновлен')

    reorder_questions.short_description = "🔢 Перенумеровать"


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    """Админка вариантов ответов"""
    list_display = ('text_preview', 'question_link', 'order',
                    'value_preview')
    list_filter = ('question__category', 'question')
    search_fields = ('text', 'question__text')
    list_editable = ('order',)
    ordering = ('question__order', 'order', 'id')

    fieldsets = (
        ('Основная информация', {
            'fields': ('question', 'text', 'order')
        }),
        ('Значение для алгоритма', {
            'fields': ('value',),
            'description': 'JSON с весами для персонажей'
        }),
    )

    def text_preview(self, obj):
        """Превью текста ответа"""
        return f"{obj.text[:50]}..." if len(obj.text) > 50 else obj.text

    text_preview.short_description = 'Ответ'

    def question_link(self, obj):
        """Ссылка на вопрос"""
        url = f"/admin/api/question/{obj.question.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.question.text[:30] + "..." if len(obj.question.text) > 30 else obj.question.text
        )

    question_link.short_description = 'Вопрос'

    def value_preview(self, obj):
        """Превью значения JSON"""
        value_str = str(obj.value)
        return f"{value_str[:30]}..." if len(value_str) > 30 else value_str

    value_preview.short_description = 'Значение'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    """Админка результатов тестов"""
    # Убрал SwipeInline, так как Swipe не связан с TestResult

    list_display = ('user_link', 'character_link', 'match_score',
                    'completed_at')
    list_filter = ('character', 'completed_at')
    search_fields = ('user__username', 'user__email', 'character__name')
    readonly_fields = ('completed_at', 'created_at', 'updated_at', 'score_preview', 'match_score_calc')

    fieldsets = (
        ('Результат', {
            'fields': ('user', 'character')
        }),
        ('Детали', {
            'fields': ('score_preview', 'match_score_calc'),
            'classes': ('collapse',)
        }),
        ('Время', {
            'fields': ('completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = f"/admin/users/customuser/{obj.user.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user.username
        )

    user_link.short_description = 'Пользователь'

    def character_link(self, obj):
        """Ссылка на персонажа"""
        if obj.character:
            url = f"/admin/characters/brainrotcharacter/{obj.character.id}/change/"
            return format_html(
                '<a href="{}" style="color: #4CAF50;">{}</a>',
                url, obj.character.name
            )
        return "—"

    character_link.short_description = 'Результат'

    def match_score(self, obj):
        """Отображение процента совпадения"""
        if obj.score:
            max_score = max(obj.score.values()) if obj.score else 0
            total_possible = len(obj.score) * 10  # Примерный расчет
            if total_possible > 0:
                percentage = (max_score / total_possible) * 100
                color = '#4CAF50' if percentage > 70 else '#FF9800' if percentage > 40 else '#f44336'
                return format_html(
                    '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                    color, percentage
                )
        return "—"

    match_score.short_description = 'Совпадение'

    def score_preview(self, obj):
        """Превью JSON с баллами"""
        if obj.score:
            score_str = ", ".join([f"{k}: {v}" for k, v in list(obj.score.items())[:5]])
            return score_str + ("..." if len(obj.score) > 5 else "")
        return "Нет данных"

    score_preview.short_description = 'Баллы по персонажам'

    def match_score_calc(self, obj):
        """Расчет процента совпадения"""
        if obj.score and obj.character and obj.character.id in obj.score:
            char_score = obj.score[str(obj.character.id)]
            max_score = max(obj.score.values())
            if max_score > 0:
                percentage = (char_score / max_score) * 100
                return f"{percentage:.1f}% (балл: {char_score}, максимум: {max_score})"
        return "Не рассчитано"

    match_score_calc.short_description = 'Расчет совпадения'


@admin.register(Swipe)
class SwipeAdmin(admin.ModelAdmin):
    """Админка свайпов"""
    list_display = ('user_link', 'character_link', 'swipe_type_display',
                    'timestamp', 'popularity_impact')
    list_filter = ('swipe_type', 'timestamp', 'character__category')
    search_fields = ('user__username', 'character__name')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'created_at', 'updated_at')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'character', 'swipe_type')
        }),
        ('Время', {
            'fields': ('timestamp', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['convert_to_like', 'convert_to_dislike', 'delete_old_swipes']

    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = f"/admin/users/customuser/{obj.user.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user.username
        )

    user_link.short_description = 'Пользователь'

    def character_link(self, obj):
        """Ссылка на персонажа"""
        url = f"/admin/characters/brainrotcharacter/{obj.character.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.character.name
        )

    character_link.short_description = 'Персонаж'

    def swipe_type_display(self, obj):
        """Отображение типа свайпа с иконкой"""
        icons = {
            'like': '❤️',
            'dislike': '👎',
            'super_like': '⭐',
        }
        colors = {
            'like': '#4CAF50',
            'dislike': '#f44336',
            'super_like': '#FF9800',
        }
        icon = icons.get(obj.swipe_type, '📌')
        color = colors.get(obj.swipe_type, '#999999')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_swipe_type_display()
        )

    swipe_type_display.short_description = 'Тип свайпа'

    def popularity_impact(self, obj):
        """Влияние на популярность персонажа"""
        impacts = {
            'like': '+1',
            'dislike': '-1',
            'super_like': '+3',
        }
        impact = impacts.get(obj.swipe_type, '0')
        color = '#4CAF50' if impact.startswith('+') else '#f44336' if impact.startswith('-') else '#999999'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, impact
        )

    popularity_impact.short_description = 'Влияние'

    def convert_to_like(self, request, queryset):
        """Конвертировать в лайки"""
        updated = queryset.update(swipe_type='like')
        self.message_user(request, f'{updated} свайпов конвертированы в лайки')

    convert_to_like.short_description = "❤️ Конвертировать в лайки"

    def convert_to_dislike(self, request, queryset):
        """Конвертировать в дизлайки"""
        updated = queryset.update(swipe_type='dislike')
        self.message_user(request, f'{updated} свайпов конвертированы в дизлайки')

    convert_to_dislike.short_description = "👎 Конвертировать в дизлайки"

    def delete_old_swipes(self, request, queryset):
        """Удалить старые свайпы (старше 30 дней)"""
        from django.utils import timezone
        from datetime import timedelta

        month_ago = timezone.now() - timedelta(days=30)
        old_swipes = queryset.filter(timestamp__lt=month_ago)
        count = old_swipes.count()
        old_swipes.delete()
        self.message_user(request, f'Удалено {count} старых свайпов')

    delete_old_swipes.short_description = "🗑️ Удалить старые (>30 дней)"


@admin.register(CompatibilityMatrix)
class CompatibilityMatrixAdmin(admin.ModelAdmin):
    """Админка матрицы совместимости"""
    list_display = ('character_1_link', 'character_2_link', 'compatibility_bar',
                    'tags_display')
    list_filter = ('character_1__category', 'character_2__category')
    search_fields = ('character_1__name', 'character_2__name', 'description', 'tags')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Персонажи', {
            'fields': ('character_1', 'character_2')
        }),
        ('Совместимость', {
            'fields': ('score', 'description', 'tags')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['recalculate_compatibility', 'generate_all_compatibility']

    def character_1_link(self, obj):
        """Ссылка на первого персонажа"""
        url = f"/admin/characters/brainrotcharacter/{obj.character_1.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.character_1.name
        )

    character_1_link.short_description = 'Персонаж 1'

    def character_2_link(self, obj):
        """Ссылка на второго персонажа"""
        url = f"/admin/characters/brainrotcharacter/{obj.character_2.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.character_2.name
        )

    character_2_link.short_description = 'Персонаж 2'

    def compatibility_bar(self, obj):
        """Визуализация совместимости"""
        percentage = obj.score * 100
        if percentage >= 80:
            color = '#4CAF50'
            emoji = '💚'
        elif percentage >= 60:
            color = '#FF9800'
            emoji = '💛'
        elif percentage >= 40:
            color = '#FFC107'
            emoji = '💛'
        else:
            color = '#f44336'
            emoji = '❤️‍🩹'

        return format_html(
            '{} <div style="width: 100px; display: inline-block; margin-left: 10px; '
            'background: #e0e0e0; border-radius: 3px; vertical-align: middle;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{:.1f}%</div></div>',
            emoji, percentage, color, percentage
        )

    compatibility_bar.short_description = 'Совместимость'

    def tags_display(self, obj):
        """Отображение тегов"""
        if obj.tags:
            tags_html = []
            for tag in obj.tags[:3]:  # Показываем только первые 3 тега
                tags_html.append(
                    f'<span style="background: #E3F2FD; color: #1976D2; '
                    f'padding: 2px 6px; border-radius: 10px; font-size: 11px; '
                    f'margin-right: 4px;">{tag}</span>'
                )
            return format_html("".join(tags_html))
        return "—"

    tags_display.short_description = 'Теги'

    def recalculate_compatibility(self, request, queryset):
        """Пересчитать совместимость"""
        from .views import CompatibilityView
        view = CompatibilityView()

        recalculated = 0
        for comp in queryset:
            new_score = view.calculate_compatibility(comp.character_1, comp.character_2)
            comp.score = new_score
            comp.description = view.generate_compatibility_description(
                comp.character_1, comp.character_2, new_score
            )
            comp.save()
            recalculated += 1

        self.message_user(request, f'Пересчитано {recalculated} совместимостей')

    recalculate_compatibility.short_description = "🔄 Пересчитать совместимость"

    def generate_all_compatibility(self, request, queryset):
        """Сгенерировать все совместимости"""
        from characters.models import BrainRotCharacter
        from .views import CompatibilityView

        characters = BrainRotCharacter.objects.filter(is_active=True)
        view = CompatibilityView()
        created = 0

        for i, char1 in enumerate(characters):
            for char2 in characters[i + 1:]:
                CompatibilityMatrix.objects.get_or_create(
                    character_1=char1,
                    character_2=char2,
                    defaults={
                        'score': view.calculate_compatibility(char1, char2),
                        'description': view.generate_compatibility_description(char1, char2,
                                                                               view.calculate_compatibility(char1,
                                                                                                            char2))
                    }
                )
                created += 1

        self.message_user(request, f'Создано {created} записей совместимости')

    generate_all_compatibility.short_description = "🧮 Сгенерировать все совместимости"