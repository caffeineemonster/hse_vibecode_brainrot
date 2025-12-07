# characters/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (BrainRotCharacter, CharacterTrait,
                     UserCharacterProfile, UserTraitValue, CustomTrait)


@admin.register(BrainRotCharacter)
class BrainRotCharacterAdmin(admin.ModelAdmin):
    """Админка для BrainRot персонажей"""
    list_display = ('name', 'category', 'year_emerged', 'popularity_score',
                    'traits_count', 'user_count', 'image_preview', 'is_active')
    list_filter = ('category', 'is_active', 'year_emerged')
    search_fields = ('name', 'description', 'origin', 'iconic_phrase')
    list_editable = ('popularity_score', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Детали', {
            'fields': ('origin', 'year_emerged', 'iconic_phrase', 'image')
        }),
        ('Статистика', {
            'fields': ('popularity_score', 'is_active')
        }),
    )

    def image_preview(self, obj):
        """Предпросмотр изображения"""
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 5px;" />',
                               obj.image.url)
        return "Нет изображения"

    image_preview.short_description = 'Изображение'

    def traits_count(self, obj):
        return obj.traits.count()

    traits_count.short_description = 'Признаков'

    def user_count(self, obj):
        return obj.user_profiles.count()

    user_count.short_description = 'Пользователей'


@admin.register(CharacterTrait)
class CharacterTraitAdmin(admin.ModelAdmin):
    """Админка для признаков персонажей"""
    list_display = ('name', 'trait_type', 'character', 'is_global',
                    'default_value', 'min_value', 'max_value')
    list_filter = ('trait_type', 'is_global', 'character')
    search_fields = ('name', 'description')
    list_editable = ('default_value', 'min_value', 'max_value')

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'trait_type', 'description', 'character', 'is_global')
        }),
        ('Значения', {
            'fields': ('min_value', 'max_value', 'default_value')
        }),
    )


class UserTraitValueInline(admin.TabularInline):
    """Inline для значений признаков пользователя"""
    model = UserTraitValue
    extra = 1
    fields = ('trait', 'value', 'is_active', 'custom_note')
    autocomplete_fields = ['trait']


class CustomTraitInline(admin.TabularInline):
    """Inline для кастомных признаков"""
    model = CustomTrait
    extra = 0
    fields = ('name', 'trait_type', 'value', 'description', 'is_public')
    readonly_fields = ('likes_count', 'created_at')


@admin.register(UserCharacterProfile)
class UserCharacterProfileAdmin(admin.ModelAdmin):
    """Админка для профилей персонажей пользователей"""
    list_display = ('user', 'main_character', 'character_level',
                    'xp_points', 'is_public', 'show_in_search', 'created_at')
    list_filter = ('is_public', 'show_in_search', 'main_character__category')
    search_fields = ('user__username', 'user__email', 'custom_description')
    autocomplete_fields = ['user', 'main_character']
    filter_horizontal = ['additional_characters']

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'main_character', 'additional_characters',
                       'custom_description')
        }),
        ('Настройки', {
            'fields': ('is_public', 'show_in_search')
        }),
        ('Прогресс', {
            'fields': ('character_level', 'xp_points')
        }),
    )

    inlines = [UserTraitValueInline, CustomTraitInline]

    readonly_fields = ('created_at', 'updated_at')

    actions = ['reset_xp', 'increase_level']

    def reset_xp(self, request, queryset):
        """Сбросить опыт выбранных профилей"""
        updated = queryset.update(xp_points=0, character_level=1)
        self.message_user(request, f'{updated} профилей сброшено')

    reset_xp.short_description = "Сбросить опыт и уровень"

    def increase_level(self, request, queryset):
        """Повысить уровень выбранных профилей"""
        for profile in queryset:
            profile.add_xp(100)
        self.message_user(request, f'{queryset.count()} профилей улучшено')

    increase_level.short_description = "Повысить уровень (+100 XP)"


@admin.register(UserTraitValue)
class UserTraitValueAdmin(admin.ModelAdmin):
    """Админка для значений признаков"""
    list_display = ('user_profile', 'trait', 'value', 'is_active', 'last_used')
    list_filter = ('is_active', 'trait__trait_type', 'trait__character')
    search_fields = ('user_profile__user__username', 'trait__name', 'custom_note')
    list_editable = ('value', 'is_active')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user_profile', 'trait')
        }),
        ('Значение', {
            'fields': ('value', 'custom_note', 'is_active')
        }),
    )

    readonly_fields = ('last_used',)


@admin.register(CustomTrait)
class CustomTraitAdmin(admin.ModelAdmin):
    """Админка для кастомных признаков"""
    list_display = ('name', 'user_profile', 'trait_type', 'value',
                    'is_public', 'likes_count', 'created_at')
    list_filter = ('trait_type', 'is_public')
    search_fields = ('name', 'description', 'user_profile__user__username')
    list_editable = ('value', 'is_public')

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
    )

    readonly_fields = ('created_at', 'updated_at', 'likes_count')