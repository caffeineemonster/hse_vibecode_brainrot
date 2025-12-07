# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views_auth import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r'swipes', views.SwipeViewSet, basename='swipe')

urlpatterns = [
    # API аутентификации и профиля
    path('', include('api.urls_auth')),

    # Основное API
    path('characters/', views.CharacterListView.as_view(), name='character-list'),
    path('characters/recommended/', views.RecommendedCharactersView.as_view(),
         name='character-recommended'),

    path('questions/', views.QuestionListView.as_view(), name='question-list'),
    path('test/submit/', views.TestSubmitView.as_view(), name='test-submit'),

    path('compatibility/<int:char1_id>/<int:char2_id>/',
         views.CompatibilityView.as_view(), name='compatibility'),

    path('matches/suggestions/', views.MatchSuggestionView.as_view(),
         name='match-suggestions'),

    path('swipe/stats/', views.SwipeStatsView.as_view(), name='swipe-stats'),

    # Подключаем роутер для свайпов
    path('', include(router.urls)),

    # Для просмотра API в браузере
    path('api-auth/', include('rest_framework.urls')),
    path('chat/', include('chat.urls')),
]