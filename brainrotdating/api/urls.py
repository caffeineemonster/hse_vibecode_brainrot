# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'swipes', views.SwipeViewSet, basename='swipe')

urlpatterns = [
    # GET /api/characters/ - список персонажей для свайпера
    path('characters/', views.CharacterListView.as_view(), name='character-list'),

    # Убрал неправильный вызов, добавил отдельный эндпоинт
    # GET /api/characters/recommended/ - рекомендованные персонажи
    path('characters/recommended/', views.RecommendedCharactersView.as_view(),
         name='character-recommended'),

    # GET /api/questions/ - вопросы теста
    path('questions/', views.QuestionListView.as_view(), name='question-list'),

    # POST /api/test/submit/ - отправить ответы, получить результат
    path('test/submit/', views.TestSubmitView.as_view(), name='test-submit'),

    # GET /api/compatibility/{char1_id}/{char2_id}/ - совместимость персонажей
    path('compatibility/<int:char1_id>/<int:char2_id>/',
         views.CompatibilityView.as_view(), name='compatibility'),

    # Дополнительные эндпоинты
    path('matches/suggestions/', views.MatchSuggestionView.as_view(),
         name='match-suggestions'),

    # Статистика свайпов (отдельный view)
    path('swipe/stats/', views.SwipeStatsView.as_view(), name='swipe-stats'),

    # Подключаем роутер для свайпов (GET, POST, DELETE)
    path('', include(router.urls)),
]