# api/urls_auth.py (создай новый файл)
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from .views_auth import (
    RegisterView, LoginView, LogoutView, UserProfileView,
    ChangePasswordView, DeleteAccountView, ValidateTokenView,
    CustomTokenObtainPairView, CustomTokenRefreshView
)
from .views_profile import UserStatsView, UserMatchesView, UserActivityView

urlpatterns = [
    # Аутентификация
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/validate/', ValidateTokenView.as_view(), name='validate_token'),

    # Профиль пользователя
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    path('auth/profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/profile/delete/', DeleteAccountView.as_view(), name='delete_account'),

    # Статистика и активность
    path('auth/profile/stats/', UserStatsView.as_view(), name='user_stats'),
    path('auth/profile/matches/', UserMatchesView.as_view(), name='user_matches'),
    path('auth/profile/activity/', UserActivityView.as_view(), name='user_activity'),
]