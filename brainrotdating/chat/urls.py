# chat/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'matches', views.MatchViewSet, basename='match')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'blocks', views.ChatBlockViewSet, basename='block')
router.register(r'reports', views.ChatReportViewSet, basename='report')
router.register(r'presence', views.UserPresenceViewSet, basename='presence')

urlpatterns = [
    # REST API
    path('', include(router.urls)),

    # Настройки чата
    path('settings/', views.ChatSettingsView.as_view(), name='chat_settings'),

    # Поиск и онлайн пользователи
    path('online/', views.OnlineUsersView.as_view(), name='online_users'),
    path('search/', views.ChatSearchView.as_view(), name='chat_search'),
]