# api/views_auth.py (создай новый файл)
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils import timezone
from .serializers import (
    RegisterSerializer, LoginSerializer, UserProfileSerializer,
    ChangePasswordSerializer, UpdateProfileSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Обновляем last_login
        user.last_login = timezone.now()
        user.save()

        # Создаем JWT токены
        refresh = RefreshToken.for_user(user)

        # Создаем BrainRot профиль (должно создаться через сигнал)
        if hasattr(user, 'create_brainrot_profile'):
            user.create_brainrot_profile()

        return Response({
            'user': UserProfileSerializer(user, context=self.get_serializer_context()).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Регистрация успешна! Добро пожаловать в BrainRot Dating! 🎉'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Вход пользователя"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Обновляем last_login
            user.last_login = timezone.now()
            user.save()

            # Создаем JWT токены
            refresh = RefreshToken.for_user(user)

            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'Вход выполнен успешно!'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Выход пользователя"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Выход выполнен успешно"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля пользователя"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Используем UpdateProfileSerializer для обновления
        serializer = UpdateProfileSerializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Возвращаем полный профиль
        profile_serializer = UserProfileSerializer(instance)
        return Response(profile_serializer.data)


class ChangePasswordView(generics.UpdateAPIView):
    """Смена пароля"""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Устанавливаем новый пароль
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # Делаем рефреш токенов
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Пароль успешно изменен',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteAccountView(APIView):
    """Удаление аккаунта"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user

        # Можно добавить дополнительные проверки
        # Например, подтверждение через email

        # Деактивируем аккаунт вместо полного удаления (мягкое удаление)
        user.is_active = False
        user.email = f"deleted_{user.id}_{user.email}"
        user.username = f"deleted_{user.id}_{user.username}"
        user.save()

        return Response({
            'message': 'Аккаунт успешно деактивирован. Вы можете восстановить его в течение 30 дней.'
        }, status=status.HTTP_200_OK)


class ValidateTokenView(APIView):
    """Проверка валидности токена"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'valid': True,
            'user': UserProfileSerializer(request.user).data
        }, status=status.HTTP_200_OK)


# JWT Views с кастомной логикой
class CustomTokenObtainPairView(TokenObtainPairView):
    """Кастомный вход с JWT"""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Получаем пользователя
            username = request.data.get('username')
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)

            # Обновляем last_login
            user.last_login = timezone.now()
            user.save()

            # Добавляем данные пользователя в ответ
            response.data['user'] = UserProfileSerializer(user).data
            response.data['message'] = 'Вход выполнен успешно!'

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """Кастомный обновление токена"""
    pass


# api/views_auth.py (дополнение)
class VerifyEmailView(APIView):
    """Верификация email"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.email_verified = True
            user.save()
            return Response({'message': 'Email успешно подтвержден'})

        return Response({'error': 'Ссылка недействительна'}, status=400)


class RequestPasswordResetView(APIView):
    """Запрос на восстановление пароля"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()

        if user:
            # Отправка email с токеном
            pass

        return Response({'message': 'Если email существует, инструкции отправлены'})