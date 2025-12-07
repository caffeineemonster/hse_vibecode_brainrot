# users/actions.py
from django.contrib import messages
from django.utils import timezone


def assign_age_category(modeladmin, request, queryset):
    """Назначить возрастную категорию выбранным пользователям"""
    updated = 0
    for user in queryset:
        if user.assign_age_category():
            updated += 1
    messages.success(request, f'Возрастная категория назначена {updated} пользователям')


assign_age_category.short_description = "Назначить возрастную категорию"


def generate_test_users(modeladmin, request, queryset):
    """Сгенерировать тестовых пользователей"""
    from django.contrib.auth.hashers import make_password
    from users.models import CustomUser
    from faker import Faker

    fake = Faker('ru_RU')
    users_created = 0

    for i in range(10):
        try:
            user = CustomUser.objects.create(
                username=f'testuser_{i}_{fake.user_name()}',
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password=make_password('test123'),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=60),
                city=fake.city(),
                is_active=True
            )
            users_created += 1
        except:
            continue

    messages.success(request, f'Создано {users_created} тестовых пользователей')


generate_test_users.short_description = "Создать тестовых пользователей"