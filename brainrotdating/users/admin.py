# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import CustomUser, AgeCategory
from characters.models import UserCharacterProfile, UserTraitValue, CustomTrait


# ========== INLINE МОДЕЛИ ==========

class UserCharacterProfileInline(admin.StackedInline):
    """Inline профиля персонажа пользователя"""
    model = UserCharacterProfile
    can_delete = False
    verbose_name_plural = 'BrainRot профиль'
    fields = ('main_character', 'additional_characters', 'character_level',
              'xp_points', 'is_public', 'show_in_search')
    filter_horizontal = ('additional_characters',)
    readonly_fields = ('character_level', 'xp_points')

    def has_add_permission(self, request, obj=None):
        return False


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

@admin.register(AgeCategory)
class AgeCategoryAdmin(admin.ModelAdmin):
    """Админка возрастных категорий"""
    list_display = ('name', 'generation', 'subcategory', 'min_age', 'max_age',
                    'birth_year_from', 'birth_year_to', 'user_count', 'is_active')
    list_filter = ('generation',)
    search_fields = ('name', 'subcategory', 'description')
    list_editable = ('min_age', 'max_age')
    ordering = ('-birth_year_from',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'generation', 'subcategory', 'description')
        }),
        ('Возрастные границы', {
            'fields': ('min_age', 'max_age', 'birth_year_from', 'birth_year_to')
        }),
    )

    actions = ['activate_categories', 'deactivate_categories']

    def user_count(self, obj):
        return obj.users.count()

    user_count.short_description = '👥 Пользователей'

    def is_active(self, obj):
        return obj.users.exists()

    is_active.short_description = 'Активна'
    is_active.boolean = True

    def activate_categories(self, request, queryset):
        """Активировать выбранные категории"""
        self.message_user(request, f'{queryset.count()} категорий активировано')

    activate_categories.short_description = "✅ Активировать категории"

    def deactivate_categories(self, request, queryset):
        """Деактивировать выбранные категории"""
        self.message_user(request, f'{queryset.count()} категорий деактивировано')

    deactivate_categories.short_description = "❌ Деактивировать категории"


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Расширенная админка пользователей"""
    inlines = [UserCharacterProfileInline]

    # Отображение в списке
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'age_display', 'age_category', 'city',
                    'brainrot_character_display', 'is_staff', 'is_active')
    list_filter = ('age_category', 'is_staff', 'is_active', 'is_superuser',
                   'city', 'brainrot_profile__main_character')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'city')
    ordering = ('-date_joined',)

    # Группировка полей в форме редактирования
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Персональная информация'), {
            'fields': ('first_name', 'last_name', 'email', 'birth_date',
                       'age_category', 'phone', 'city', 'bio')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined')
        }),
    )

    # Поля только для чтения
    readonly_fields = ('last_login', 'date_joined')

    # Форма создания пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2',
                       'first_name', 'last_name', 'birth_date', 'city'),
        }),
    )

    # Действия
    actions = ['assign_age_categories', 'create_brainrot_profiles',
               'export_users_csv']

    def age_display(self, obj):
        """Отображение возраста"""
        age = obj.age
        return f"{age} лет" if age else "—"

    age_display.short_description = 'Возраст'

    def brainrot_character_display(self, obj):
        """Отображение BrainRot персонажа"""
        character = obj.brainrot_character
        if character:
            return format_html('<span style="color: #4CAF50;">{}</span>', character.name)
        return format_html('<span style="color: #f44336;">Не выбран</span>')

    brainrot_character_display.short_description = 'BrainRot персонаж'

    def assign_age_categories(self, request, queryset):
        """Назначить возрастные категории выбранным пользователям"""
        updated = 0
        for user in queryset:
            if user.assign_age_category():
                updated += 1
        self.message_user(request, f'Возрастные категории назначены {updated} пользователям')

    assign_age_categories.short_description = "🎯 Назначить возрастные категории"

    def create_brainrot_profiles(self, request, queryset):
        """Создать BrainRot профили для пользователей"""
        created = 0
        for user in queryset:
            if user.create_brainrot_profile():
                created += 1
        self.message_user(request, f'Создано {created} BrainRot профилей')

    create_brainrot_profiles.short_description = "🧠 Создать BrainRot профили"