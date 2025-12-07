# chat/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import FileExtensionValidator

User = get_user_model()


class Match(models.Model):
    """Мэтч между двумя пользователями"""
    STATUS_CHOICES = [
        ('pending', '⏳ Ожидание'),
        ('accepted', '✅ Принят'),
        ('rejected', '❌ Отклонен'),
        ('expired', '⏰ Истек'),
    ]

    user_1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='matches_as_user_1',
        verbose_name="Пользователь 1"
    )
    user_2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='matches_as_user_2',
        verbose_name="Пользователь 2"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус мэтча"
    )

    # На основе чего создан мэтч
    match_type = models.CharField(
        max_length=50,
        choices=[
            ('mutual_like', 'Взаимный лайк'),
            ('test_compatibility', 'Совместимость по тесту'),
            ('admin_generated', 'Создан администратором'),
            ('manual', 'Вручную'),
        ],
        default='mutual_like',
        verbose_name="Тип мэтча"
    )

    # Совместимость при создании
    compatibility_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Совместимость",
        help_text="От 0.0 до 1.0"
    )

    # Время
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")
    matched_at = models.DateTimeField(null=True, blank=True, verbose_name="Время мэтча")
    expired_at = models.DateTimeField(null=True, blank=True, verbose_name="Истекает")

    # Настройки чата
    is_chat_active = models.BooleanField(default=True, verbose_name="Чат активен")
    last_message_at = models.DateTimeField(null=True, blank=True, verbose_name="Последнее сообщение")

    class Meta:
        verbose_name = "Мэтч"
        verbose_name_plural = "Мэтчи"
        unique_together = ['user_1', 'user_2']
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        return f"{self.user_1.username} ↔ {self.user_2.username} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем matched_at при принятии
        if self.status == 'accepted' and not self.matched_at:
            self.matched_at = timezone.now()

        # Устанавливаем время истечения (24 часа для ожидания)
        if self.status == 'pending' and not self.expired_at:
            self.expired_at = timezone.now() + timezone.timedelta(hours=24)

        super().save(*args, **kwargs)

    @property
    def participants(self):
        """Участники мэтча"""
        return [self.user_1, self.user_2]

    @property
    def get_unread_count(self, user):
        """Количество непрочитанных сообщений для пользователя"""
        return self.messages.filter(
            read_at__isnull=True
        ).exclude(
            sender=user
        ).count()

    def get_other_user(self, user):
        """Получить второго пользователя в мэтче"""
        if user == self.user_1:
            return self.user_2
        return self.user_1


class Message(models.Model):
    """Сообщение в чате"""
    MESSAGE_TYPES = [
        ('text', '📝 Текст'),
        ('image', '🖼️ Изображение'),
        ('video', '🎥 Видео'),
        ('audio', '🎵 Аудио'),
        ('sticker', '😺 Стикер'),
        ('system', '⚙️ Системное'),
        ('brainrot_gif', '🌀 BrainRot GIF'),
    ]

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Мэтч"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="Отправитель"
    )

    # Тип и содержание
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text',
        verbose_name="Тип сообщения"
    )
    content = models.TextField(verbose_name="Текст сообщения", blank=True)

    # Медиа файлы
    media_file = models.FileField(
        upload_to='chat_media/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Медиа файл",
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm', 'mp3', 'wav']
            )
        ]
    )
    thumbnail = models.ImageField(
        upload_to='chat_thumbnails/',
        blank=True,
        null=True,
        verbose_name="Превью медиа"
    )

    # BrainRot контент
    brainrot_character = models.ForeignKey(
        'characters.BrainRotCharacter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="BrainRot персонаж",
        help_text="Персонаж, связанный с сообщением"
    )
    is_brainrot_reaction = models.BooleanField(
        default=False,
        verbose_name="BrainRot реакция",
        help_text="Сообщение является реакцией BrainRot"
    )

    # Статус сообщения
    is_edited = models.BooleanField(default=False, verbose_name="Редактировано")
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Удалено в")

    # Временные метки
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Отправлено")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Доставлено")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Прочитано")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="Редактировано в")

    # Метаданные
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP адрес")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['sent_at']
        indexes = [
            models.Index(fields=['match', 'sent_at']),
            models.Index(fields=['sender', 'sent_at']),
        ]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}..."

    def save(self, *args, **kwargs):
        # Обновляем время последнего сообщения в мэтче
        if not self.is_deleted:
            self.match.last_message_at = self.sent_at
            self.match.save(update_fields=['last_message_at'])

        super().save(*args, **kwargs)

    @property
    def is_media(self):
        """Является ли сообщение медиа"""
        return self.message_type in ['image', 'video', 'audio']

    @property
    def display_content(self):
        """Отображаемое содержимое (с учетом удаления)"""
        if self.is_deleted:
            return "🗑️ Сообщение удалено"
        if self.is_edited:
            return f"{self.content} (ред.)"
        return self.content


class Reaction(models.Model):
    """Реакция на сообщение"""
    REACTION_CHOICES = [
        ('like', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('angry', '😠'),
        ('brainrot', '🌀'),
        ('fire', '🔥'),
        ('heart_eyes', '😍'),
    ]

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name="Сообщение"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_reactions',
        verbose_name="Пользователь"
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=REACTION_CHOICES,
        verbose_name="Тип реакции"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Реакция"
        verbose_name_plural = "Реакции"
        unique_together = ['message', 'user']

    def __str__(self):
        return f"{self.user.username} → {self.get_reaction_type_display()}"


class ChatSettings(models.Model):
    """Настройки чата для пользователя"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='chat_settings',
        verbose_name="Пользователь"
    )

    # Уведомления
    enable_notifications = models.BooleanField(default=True, verbose_name="Включить уведомления")
    sound_notifications = models.BooleanField(default=True, verbose_name="Звуковые уведомления")
    vibration_notifications = models.BooleanField(default=True, verbose_name="Вибрация")
    notification_sound = models.CharField(
        max_length=50,
        default='default',
        choices=[
            ('default', '🔔 По умолчанию'),
            ('soft', '🔕 Тихий'),
            ('brainrot', '🌀 BrainRot'),
            ('none', '🚫 Без звука'),
        ],
        verbose_name="Звук уведомлений"
    )

    # Приватность
    show_online_status = models.BooleanField(default=True, verbose_name="Показывать статус онлайн")
    show_last_seen = models.BooleanField(default=True, verbose_name="Показывать 'был(а) в сети'")
    allow_typing_indicator = models.BooleanField(default=True, verbose_name="Показывать 'печатает...'")

    # Сообщения
    save_media_automatically = models.BooleanField(default=False, verbose_name="Автосохранение медиа")
    auto_delete_messages = models.IntegerField(
        default=0,
        choices=[
            (0, 'Никогда'),
            (86400, 'Через 24 часа'),
            (604800, 'Через 7 дней'),
            (2592000, 'Через 30 дней'),
        ],
        verbose_name="Автоудаление сообщений (секунды)"
    )

    # Тема
    theme = models.CharField(
        max_length=20,
        default='light',
        choices=[
            ('light', '☀️ Светлая'),
            ('dark', '🌙 Темная'),
            ('brainrot', '🌀 BrainRot'),
            ('midnight', '🌌 Полночь'),
        ],
        verbose_name="Тема чата"
    )

    # Безопасность
    block_strangers = models.BooleanField(default=False, verbose_name="Блокировать незнакомцев")
    require_verification = models.BooleanField(default=False, verbose_name="Требовать верификацию")
    report_inappropriate = models.BooleanField(default=True, verbose_name="Сообщать о неприемлемом контенте")

    # Время
    quiet_hours_start = models.TimeField(null=True, blank=True, verbose_name="Тихие часы: начало")
    quiet_hours_end = models.TimeField(null=True, blank=True, verbose_name="Тихие часы: конец")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Настройки чата"
        verbose_name_plural = "Настройки чатов"

    def __str__(self):
        return f"Настройки чата: {self.user.username}"


class UserPresence(models.Model):
    """Онлайн статус пользователя"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='presence',
        verbose_name="Пользователь"
    )

    # Статус
    status = models.CharField(
        max_length=20,
        default='offline',
        choices=[
            ('online', '🟢 Онлайн'),
            ('away', '🟡 Отошел'),
            ('busy', '🔴 Занят'),
            ('invisible', '⚫ Невидимка'),
            ('offline', '⚪ Оффлайн'),
        ],
        verbose_name="Статус"
    )

    # Активность
    last_seen = models.DateTimeField(default=timezone.now, verbose_name="Был(а) в сети")
    last_activity = models.DateTimeField(default=timezone.now, verbose_name="Последняя активность")
    is_typing = models.BooleanField(default=False, verbose_name="Печатает")
    current_chat = models.ForeignKey(
        Match,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Текущий чат"
    )

    # Устройство
    device_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('web', '🌐 Веб'),
            ('android', '🤖 Android'),
            ('ios', '🍎 iOS'),
            ('desktop', '💻 Десктоп'),
        ],
        verbose_name="Тип устройства"
    )
    app_version = models.CharField(max_length=20, blank=True, verbose_name="Версия приложения")

    # Соединение
    socket_id = models.CharField(max_length=100, blank=True, verbose_name="ID сокета")
    connection_count = models.IntegerField(default=0, verbose_name="Количество соединений")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Статус пользователя"
        verbose_name_plural = "Статусы пользователей"

    def __str__(self):
        return f"{self.user.username}: {self.get_status_display()}"

    @property
    def is_online(self):
        """Проверка, онлайн ли пользователь"""
        if self.status == 'offline' or self.status == 'invisible':
            return False

        # Проверяем время последней активности (5 минут)
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
        return self.last_activity > five_minutes_ago


class ChatBlock(models.Model):
    """Блокировка пользователей в чате"""
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_users',
        verbose_name="Кто блокирует"
    )
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by',
        verbose_name="Кого блокируют"
    )

    reason = models.TextField(blank=True, verbose_name="Причина блокировки")
    block_type = models.CharField(
        max_length=20,
        default='full',
        choices=[
            ('full', 'Полная блокировка'),
            ('messages_only', 'Только сообщения'),
            ('profile_only', 'Только профиль'),
        ],
        verbose_name="Тип блокировки"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Заблокирован")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Истекает")

    class Meta:
        verbose_name = "Блокировка чата"
        verbose_name_plural = "Блокировки чатов"
        unique_together = ['blocker', 'blocked']

    def __str__(self):
        return f"{self.blocker.username} → {self.blocked.username}"

    @property
    def is_active(self):
        """Активна ли блокировка"""
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True


class ChatReport(models.Model):
    """Жалоба на пользователя/чат"""
    REPORT_TYPES = [
        ('inappropriate', 'Неприемлемый контент'),
        ('harassment', 'Домогательства'),
        ('spam', 'Спам'),
        ('fake_profile', 'Фейковый профиль'),
        ('underage', 'Несовершеннолетний'),
        ('other', 'Другое'),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_reports_made',
        verbose_name="Жалобщик"
    )
    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_reports_received',
        verbose_name="На кого жалуются"
    )
    match = models.ForeignKey(
        Match,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Чат"
    )

    report_type = models.CharField(
        max_length=50,
        choices=REPORT_TYPES,
        verbose_name="Тип жалобы"
    )
    description = models.TextField(verbose_name="Описание проблемы")
    evidence = models.FileField(
        upload_to='chat_reports/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Доказательства"
    )

    # Статус обработки
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', '⏳ На рассмотрении'),
            ('investigating', '🔍 Расследуется'),
            ('resolved', '✅ Решено'),
            ('dismissed', '❌ Отклонено'),
        ],
        verbose_name="Статус жалобы"
    )
    admin_notes = models.TextField(blank=True, verbose_name="Заметки администратора")
    action_taken = models.TextField(blank=True, verbose_name="Принятые меры")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Решена")

    class Meta:
        verbose_name = "Жалоба на чат"
        verbose_name_plural = "Жалобы на чаты"

    def __str__(self):
        return f"Жалоба от {self.reporter.username} на {self.reported_user.username}"