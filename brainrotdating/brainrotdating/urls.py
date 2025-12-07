# brainrotdating/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 👇 Главная страница - твоя верстка
    path('', TemplateView.as_view(template_name='frontend/index.html'), name='home'),

    # 👇 Другие фронтенд страницы (пока ведут на главную)
    path('swipe/', TemplateView.as_view(template_name='frontend/swipe.html'), name='swipe'),
    path('test/', TemplateView.as_view(template_name='frontend/test.html'), name='test'),
    path('profile/', TemplateView.as_view(template_name='frontend/index.html'), name='profile'),
    path('login/', TemplateView.as_view(template_name='frontend/login.html'), name='login'),
    path('register/', TemplateView.as_view(template_name='frontend/register.html'), name='register'),

    # Бэкенд API
    path('api/', include('api.urls')),

    # Админка
    path('admin/', admin.site.urls),

    # DRF browsable API
    path('api-auth/', include('rest_framework.urls')),
]

# 👇 Статические файлы в разработке
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)