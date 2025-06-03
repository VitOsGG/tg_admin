from django.db import models
from django.conf import settings  # Для ссылки на модель User


class TelegramChannel(models.Model):
    # id = models.AutoField(primary_key=True) # Django добавит это автоматически (порядковый номер)
    name = models.CharField(max_length=255, unique=True)
    # Это поле хранит фактический ID телеграм-канала, оно должно быть UNIQUE
    channel_id = models.BigIntegerField(unique=True, null=False, blank=False)  # Сделаем его обязательным, раз это
    # ключ для связи

    class Meta:
        db_table = 'telegram_channels'
        verbose_name = 'Telegram Канал'
        verbose_name_plural = 'Telegram Каналы'

    def __str__(self):
        # Для отображения в админке лучше использовать имя, а не ID
        return f"{self.name} (TG ID: {self.channel_id})"


class PostNews(models.Model):
    # ... другие поля ...
    news_id = models.BigIntegerField(null=True, blank=True)
    pars_text = models.TextField(null=True, blank=True)
    ai_text = models.TextField(null=True, blank=True)
    url_image = models.TextField(null=True, blank=True)
    image = models.BinaryField(null=True, blank=True)
    is_post = models.BooleanField(null=True, blank=True, default=False)
    post_time = models.DateTimeField(null=True, blank=True)

    channel = models.ForeignKey(
        TelegramChannel,
        to_field='channel_id',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts'
    )

    class Meta:
        db_table = 'post_news'
        verbose_name = 'Новость (новая)'
        verbose_name_plural = 'Новости (новые)'

    def __str__(self):
        return f"Новость ID: {self.news_id or self.id}"


class UserChannelPermission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Убедитесь, что 'TelegramChannel' - правильное имя вашей модели канала
    channel = models.ForeignKey('TelegramChannel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'channel')
        verbose_name = 'Разрешение пользователя на канал' # Исправил опечатку "Доступный пользователя"
        verbose_name_plural = 'Разрешения пользователей на каналы'

    def __str__(self):
        return f"{self.user.username} - {self.channel.name}"