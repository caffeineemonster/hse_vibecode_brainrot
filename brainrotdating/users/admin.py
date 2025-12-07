# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, AgeCategory


@admin.register(AgeCategory)
class AgeCategoryAdmin(admin.ModelAdmin):
    """Админка для возрастных категорий"""
    list_display = ('name', 'generation', 'subcategory', 'min_age', 'max_age',
                    'birth_year_from', 'birth_year_to', 'user_count')
    list_filter = ('generation',)
    search_fields = ('name', 'subcategory', 'description')
    ordering = ('-birth_year_from',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'generation', 'subcategory', 'description')
        }),
        ('Возрастные границы', {
            'fields': ('min_age', 'max_age', 'birth_year_from', 'birth_year_to')
        }),
    )

    def user_count(self, obj):
        """Количество пользователей в категории"""
        return obj.users.count()

    user_count.short_description = 'Пользователей'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Админка для кастомного пользователя"""
    # Поля для отображения в списке
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'age', 'age_category', 'city', 'is_staff', 'is_active')
    list_filter = ('age_category', 'is_staff', 'is_active', 'is_superuser', 'city')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'city')
    ordering = ('-date_joined',)

    # Фильтры сбоку
    filter_horizontal = ('groups', 'user_permissions')

    # Форма редактирования
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

    # Форма добавления
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2',
                       'first_name', 'last_name', 'birth_date'),
        }),
    )

    # Только для чтения
    readonly_fields = ('last_login', 'date_joined')

    # Действия
    actions = ['activate_users', 'deactivate_users']

    def activate_users(self, request, queryset):
        """Активировать выбранных пользователей"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} пользователей активировано')

    activate_users.short_description = "Активировать выбранных пользователей"

    def deactivate_users(self, request, queryset):
        """Деактивировать выбранных пользователей"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} пользователей деактивировано')

    deactivate_users.short_description = "Деактивировать выбранных пользователей"