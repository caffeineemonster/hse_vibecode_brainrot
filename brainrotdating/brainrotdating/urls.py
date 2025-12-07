# brainrotdating/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Админка Django
    path('admin/', admin.site.urls),

    # Все API эндпоинты
    path('api/', include('api.urls')),

    # Для авторизации (опционально, если нужен просмотр API в браузере)
    path('api-auth/', include('rest_framework.urls')),

    path('api/chat/', include('chat.urls')),
]

# Для обслуживания медиафайлов в разработке
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)