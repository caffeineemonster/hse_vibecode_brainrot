# api/urls.py - ЗАМЕНИТЬ ВЕСЬ ФАЙЛ на:
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views_auth import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r'swipes', views.SwipeViewSet, basename='swipe')

urlpatterns = [
    # API аутентификации и профиля
    path('', include('api.urls_auth')),

    # === BRAINROT ТЕСТ ===
    path('test/questions/',
         views.BrainRotTestQuestionsView.as_view(),
         name='brainrot-test-questions'),

    path('test/submit/',
         views.BrainRotTestSubmitView.as_view(),
         name='brainrot-test-submit'),

    path('test/preview/',
         views.BrainRotTestPreviewView.as_view(),
         name='brainrot-test-preview'),

    # === СВАЙПЕР ===
    path('characters/',
         views.CharacterListView.as_view(),
         name='character-list'),

    path('characters/recommended/',
         views.RecommendedCharactersView.as_view(),
         name='character-recommended'),

    # === СОВМЕСТИМОСТЬ ===
    path('compatibility/<int:char1_id>/<int:char2_id>/',
         views.CompatibilityView.as_view(),
         name='compatibility'),

    # === МЭТЧИ ===
    path('matches/suggestions/',
         views.MatchSuggestionView.as_view(),
         name='match-suggestions'),

    # === СТАТИСТИКА ===
    path('swipe/stats/',
         views.SwipeStatsView.as_view(),
         name='swipe-stats'),

    # Подключаем роутер для свайпов
    path('', include(router.urls)),

    # Для просмотра API в браузере
    path('api-auth/', include('rest_framework.urls')),

    # Чат (если нужно)
    path('chat/', include('chat.urls')),
]