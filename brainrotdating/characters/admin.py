# characters/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (BrainRotCharacter, CharacterTrait,
                     UserCharacterProfile, UserTraitValue, CustomTrait)
from users.models import CustomUser


# ========== INLINE МОДЕЛИ ==========

class CharacterTraitInline(admin.TabularInline):
    """Inline признаков персонажа"""
    model = CharacterTrait
    extra = 1
    fields = ('name', 'trait_type', 'description', 'is_global',
              'min_value', 'max_value', 'default_value')


class UserTraitValueInline(admin.TabularInline):
    """Inline значений признаков пользователя"""
    model = UserTraitValue
    extra = 1
    verbose_name_plural = 'Признаки персонажа'
    fields = ('trait', 'value', 'is_active', 'last_used')
    readonly_fields = ('last_used',)


class CustomTraitInline(admin.TabularInline):
    """Inline кастомных признаков пользователя"""
    model = CustomTrait
    extra = 0
    verbose_name_plural = 'Кастомные признаки'
    fields = ('name', 'trait_type', 'value', 'is_public', 'likes_count')
    readonly_fields = ('likes_count',)


# ========== ОСНОВНЫЕ МОДЕЛИ ==========

@admin.register(BrainRotCharacter)
class BrainRotCharacterAdmin(admin.ModelAdmin):
    """Админка BrainRot персонажей"""
    inlines = [CharacterTraitInline]

    list_display = ('name', 'category_display', 'year_emerged',
                    'popularity_score', 'traits_count', 'user_count',
                    'image_preview', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'year_emerged', 'created_at')
    search_fields = ('name', 'description', 'origin', 'iconic_phrase')
    list_editable = ('popularity_score', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'image_preview_large')

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'category', 'description', 'image')
        }),
        ('Детали', {
            'fields': ('origin', 'year_emerged', 'iconic_phrase')
        }),
        ('Статистика', {
            'fields': ('popularity_score', 'is_active')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at', 'image_preview_large'),
            'classes': ('collapse',)
        }),
    )

    actions = ['increase_popularity', 'decrease_popularity', 'duplicate_character']

    def category_display(self, obj):
        """Отображение категории с цветом"""
        colors = {
            'streamer': '#FF6B6B',
            'meme': '#4ECDC4',
            'game': '#45B7D1',
            'movie': '#96CEB4',
            'music': '#FFEAA7',
            'internet': '#DDA0DD',
        }
        color = colors.get(obj.category, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px;">{}</span>',
            color, obj.get_category_display()
        )

    category_display.short_description = 'Категория'

    def image_preview(self, obj):
        """Маленькое превью изображения в списке"""
        if obj.image:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 5px; object-fit: cover;" />',
                obj.image.url
            )
        return "🖼️"

    image_preview.short_description = ''

    def image_preview_large(self, obj):
        """Большое превью изображения в форме"""
        if obj.image:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 8px; border: 2px solid #ddd;" />',
                obj.image.url
            )
        return "Изображение не загружено"

    image_preview_large.short_description = 'Превью изображения'

    def traits_count(self, obj):
        return obj.traits.count()

    traits_count.short_description = '🎭 Признаков'

    def user_count(self, obj):
        return obj.user_profiles.count()

    user_count.short_description = '👥 Пользователей'

    def increase_popularity(self, request, queryset):
        """Увеличить популярность персонажей"""
        for character in queryset:
            character.popularity_score += 10
            character.save()
        self.message_user(request, f'Популярность {queryset.count()} персонажей увеличена')

    increase_popularity.short_description = "📈 Увеличить популярность (+10)"

    def decrease_popularity(self, request, queryset):
        """Уменьшить популярность персонажей"""
        for character in queryset:
            character.popularity_score = max(0, character.popularity_score - 10)
            character.save()
        self.message_user(request, f'Популярность {queryset.count()} персонажей уменьшена')

    decrease_popularity.short_description = "📉 Уменьшить популярность (-10)"

    def duplicate_character(self, request, queryset):
        """Дублировать выбранных персонажей"""
        duplicated = 0
        for character in queryset:
            character.pk = None
            character.name = f"{character.name} (копия)"
            character.slug = f"{character.slug}-copy"
            character.popularity_score = 0
            character.save()

            # Копируем признаки
            for trait in character.traits.all():
                trait.pk = None
                trait.character = character
                trait.save()

            duplicated += 1

        self.message_user(request, f'Создано {duplicated} копий персонажей')

    duplicate_character.short_description = "🔄 Дублировать персонажей"


@admin.register(CharacterTrait)
class CharacterTraitAdmin(admin.ModelAdmin):
    """Админка признаков персонажей"""
    list_display = ('name', 'trait_type_display', 'character_link',
                    'is_global', 'default_value', 'min_value', 'max_value',
                    'usage_count')
    list_filter = ('trait_type', 'is_global', 'character')
    search_fields = ('name', 'description', 'character__name')
    list_editable = ('default_value', 'min_value', 'max_value', 'is_global')
    list_per_page = 50

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'trait_type', 'description')
        }),
        ('Привязка', {
            'fields': ('character', 'is_global')
        }),
        ('Значения', {
            'fields': ('min_value', 'max_value', 'default_value'),
            'classes': ('wide',)
        }),
    )

    def trait_type_display(self, obj):
        """Отображение типа признака с иконкой"""
        icons = {
            'behavior': '👤',
            'speech': '💬',
            'appearance': '👁️',
            'habit': '🔄',
            'reaction': '⚡',
            'preference': '⭐',
            'skill': '🎯',
            'personality': '🧠',
        }
        icon = icons.get(obj.trait_type, '📌')
        return f"{icon} {obj.get_trait_type_display()}"

    trait_type_display.short_description = 'Тип'

    def character_link(self, obj):
        """Ссылка на персонажа"""
        if obj.character:
            url = f"/admin/characters/brainrotcharacter/{obj.character.id}/change/"
            return format_html(
                '<a href="{}">{}</a>',
                url, obj.character.name
            )
        return "Глобальный"

    character_link.short_description = 'Персонаж'

    def usage_count(self, obj):
        """Количество использований признака"""
        return obj.user_values.count()

    usage_count.short_description = '📊 Использований'


@admin.register(UserCharacterProfile)
class UserCharacterProfileAdmin(admin.ModelAdmin):
    """Админка профилей персонажей пользователей"""
    inlines = [UserTraitValueInline, CustomTraitInline]

    list_display = ('user_link', 'main_character_link', 'character_level',
                    'xp_bar', 'is_public', 'show_in_search', 'created_at')
    list_filter = ('is_public', 'show_in_search', 'main_character__category',
                   'created_at')
    search_fields = ('user__username', 'user__email', 'custom_description',
                     'main_character__name')
    autocomplete_fields = ['user', 'main_character']
    filter_horizontal = ['additional_characters']
    readonly_fields = ('created_at', 'updated_at', 'xp_percentage')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'main_character', 'additional_characters')
        }),
        ('Описание', {
            'fields': ('custom_description',),
            'classes': ('wide',)
        }),
        ('Настройки', {
            'fields': ('is_public', 'show_in_search')
        }),
        ('Прогресс', {
            'fields': ('character_level', 'xp_points', 'xp_percentage')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['reset_xp', 'increase_level', 'make_public', 'make_private']

    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = f"/admin/users/customuser/{obj.user.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user.username
        )

    user_link.short_description = 'Пользователь'

    def main_character_link(self, obj):
        """Ссылка на персонажа"""
        if obj.main_character:
            url = f"/admin/characters/brainrotcharacter/{obj.main_character.id}/change/"
            return format_html(
                '<a href="{}" style="color: #4CAF50;">{}</a>',
                url, obj.main_character.name
            )
        return "—"

    main_character_link.short_description = 'Основной персонаж'

    def xp_bar(self, obj):
        """Прогресс-бар опыта"""
        current_xp = obj.xp_points % 100
        percentage = min(100, (current_xp / 100) * 100)
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: #4CAF50; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}/100</div></div>',
            percentage, current_xp
        )

    xp_bar.short_description = 'Опыт'

    def xp_percentage(self, obj):
        """Процент заполнения уровня"""
        current_xp = obj.xp_points % 100
        return f"{current_xp}%"

    xp_percentage.short_description = 'Прогресс уровня'

    def reset_xp(self, request, queryset):
        """Сбросить опыт выбранных профилей"""
        updated = queryset.update(xp_points=0, character_level=1)
        self.message_user(request, f'{updated} профилей сброшено')

    reset_xp.short_description = "🔄 Сбросить опыт"

    def increase_level(self, request, queryset):
        """Повысить уровень выбранных профилей"""
        for profile in queryset:
            profile.add_xp(100)
        self.message_user(request, f'{queryset.count()} профилей улучшено')

    increase_level.short_description = "⬆️ Повысить уровень"

    def make_public(self, request, queryset):
        """Сделать профили публичными"""
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} профилей стали публичными')

    make_public.short_description = "🌐 Сделать публичными"

    def make_private(self, request, queryset):
        """Сделать профили приватными"""
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} профилей стали приватными')

    make_private.short_description = "🔒 Сделать приватными"


@admin.register(UserTraitValue)
class UserTraitValueAdmin(admin.ModelAdmin):
    """Админка значений признаков пользователей"""
    list_display = ('user_profile_link', 'trait_link', 'value_bar',
                    'is_active', 'last_used')
    list_filter = ('is_active', 'trait__trait_type', 'trait__character')
    search_fields = ('user_profile__user__username', 'trait__name', 'custom_note')
    list_editable = ('is_active',)
    readonly_fields = ('last_used',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('user_profile', 'trait')
        }),
        ('Значение', {
            'fields': ('value', 'custom_note')
        }),
        ('Состояние', {
            'fields': ('is_active', 'last_used')
        }),
    )

    def user_profile_link(self, obj):
        """Ссылка на профиль пользователя"""
        url = f"/admin/characters/usercharacterprofile/{obj.user_profile.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user_profile.user.username
        )

    user_profile_link.short_description = 'Пользователь'

    def trait_link(self, obj):
        """Ссылка на признак"""
        url = f"/admin/characters/charactertrait/{obj.trait.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.trait.name
        )

    trait_link.short_description = 'Признак'

    def value_bar(self, obj):
        """Визуализация значения"""
        percentage = ((obj.value - obj.trait.min_value) /
                      (obj.trait.max_value - obj.trait.min_value)) * 100
        color = '#4CAF50' if obj.value > obj.trait.default_value else '#FF9800'
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}</div></div>',
            percentage, color, obj.value
        )

    value_bar.short_description = 'Значение'


@admin.register(CustomTrait)
class CustomTraitAdmin(admin.ModelAdmin):
    """Админка кастомных признаков"""
    list_display = ('name', 'user_profile_link', 'trait_type_display',
                    'value_bar', 'is_public', 'likes_count', 'created_at')
    list_filter = ('trait_type', 'is_public', 'created_at')
    search_fields = ('name', 'description', 'user_profile__user__username')
    list_editable = ('is_public',)
    readonly_fields = ('created_at', 'updated_at', 'likes_count')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user_profile', 'name', 'trait_type', 'description')
        }),
        ('Значения', {
            'fields': ('value', 'max_value')
        }),
        ('Настройки', {
            'fields': ('is_public', 'likes_count')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['make_popular', 'reset_likes']

    def user_profile_link(self, obj):
        """Ссылка на профиль пользователя"""
        url = f"/admin/characters/usercharacterprofile/{obj.user_profile.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user_profile.user.username
        )

    user_profile_link.short_description = 'Автор'

    def trait_type_display(self, obj):
        """Отображение типа признака"""
        return obj.get_trait_type_display()

    trait_type_display.short_description = 'Тип'

    def value_bar(self, obj):
        """Визуализация значения"""
        percentage = (obj.value / obj.max_value) * 100
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: #9C27B0; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}</div></div>',
            percentage, obj.value
        )

    value_bar.short_description = 'Значение'

    def make_popular(self, request, queryset):
        """Увеличить популярность признаков"""
        for trait in queryset:
            trait.likes_count += 10
            trait.save()
        self.message_user(request, f'Популярность {queryset.count()} признаков увеличена')

    make_popular.short_description = "🔥 Увеличить популярность"

    def reset_likes(self, request, queryset):
        """Сбросить лайки признаков"""
        updated = queryset.update(likes_count=0)
        self.message_user(request, f'Лайки {updated} признаков сброшены')

    reset_likes.short_description = "🔄 Сбросить лайки"
