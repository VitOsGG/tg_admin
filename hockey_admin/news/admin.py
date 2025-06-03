from django.contrib import admin
from .models import PostNews, TelegramChannel, UserChannelPermission
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from django import forms
from django.shortcuts import render, redirect
from django.utils import timezone


@admin.register(UserChannelPermission)
class UserChannelPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel')
    list_filter = ('user', 'channel')
    search_fields = ('user__username', 'channel__name', 'channel__channel_id')
    autocomplete_fields = ['user', 'channel']  # Удобно для выбора

    def get_queryset(self, request):
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        obj.save()

    def delete_model(self, request, obj):
        obj.delete()


class PublishForm(forms.Form):
    post_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],  # формат для datetime-local без секунд
        label='Время публикации (оставьте пустым для текущего времени)'
    )


class PostNewsAdminForm(forms.ModelForm):  # Переименовали и изменили модель
    image_file = forms.FileField(required=False, label='Загрузить новое фото')
    post_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
        label='Время публикации'
    )

    class Meta:
        model = PostNews
        fields = '__all__'
        exclude = ['image']

    def save(self, commit=True):
        instance = super().save(commit=False)
        file = self.cleaned_data.get('image_file')
        if file:
            instance.image = file.read()
        if commit:
            instance.save()
        return instance


print("admin.py с PostNewsAdmin загружен")


class PostNewsAdmin(admin.ModelAdmin):
    form = PostNewsAdminForm
    list_display = ['id', 'news_id', 'ai_text_short', 'image_preview', 'channel', 'post_time', 'is_post',
                    'action_buttons']
    readonly_fields = ['image_preview']
    fields = ['news_id', 'channel', 'pars_text', 'ai_text', 'url_image', 'image_preview', 'image_file', 'is_post',
              'post_time']
    list_display_links = ['id', 'news_id']
    search_fields = ['ai_text', 'pars_text', 'news_id', 'channel__name', 'channel__channel_id']
    list_filter = ['is_post', 'channel', 'post_time']  # Можно оставить, но queryset будет уже отфильтрован

    def get_queryset(self, request):
        print(f"⚠️ PostNewsAdmin.get_queryset вызван для пользователя: {request.user.username}")
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            print("[DEBUG] Суперпользователь, возвращаем все записи")
            return qs

        allowed_channel_tg_ids = list(
            UserChannelPermission.objects
            .filter(user=request.user)
            .values_list('channel__channel_id', flat=True)
        )
        print(f"[DEBUG] Разрешённые channel_id для {request.user.username}: {allowed_channel_tg_ids}")

        filtered_qs = qs.filter(channel__channel_id__in=allowed_channel_tg_ids)
        print(f"[DEBUG] Кол-во постов после фильтрации: {filtered_qs.count()}")
        return filtered_qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Фильтруем выпадающий список для поля "channel" при редактировании/создании новости
        if db_field.name == "channel":
            if not request.user.is_superuser:
                try:
                    # Получаем объекты TelegramChannel, к которым у пользователя есть доступ
                    allowed_channels_qs = TelegramChannel.objects.filter(
                        channel_id__in=UserChannelPermission.objects
                        .filter(user=request.user)
                        .values_list('channel__channel_id', flat=True)
                    )
                    kwargs["queryset"] = allowed_channels_qs
                except Exception as e:
                    print(f"Ошибка при фильтрации поля channel: {e}")
                    kwargs["queryset"] = TelegramChannel.objects.none()

            else:  # Суперпользователь видит все каналы
                kwargs["queryset"] = TelegramChannel.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        # Разрешить добавление, только если у пользователя есть доступ хотя бы к одному каналу
        if request.user.is_superuser:
            return True
        try:
            return UserChannelPermission.objects.filter(user=request.user).exists()
        except:
            return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:  # Для страницы списка (changelist)
            return True  # Контролируется через get_queryset

        # Для конкретного объекта новости, проверяем, есть ли у пользователя доступ к каналу этой новости
        if obj.channel:  # Если у новости есть канал
            try:
                return UserChannelPermission.objects.filter(
                    user=request.user,
                    channel__channel_id=obj.channel.channel_id  # obj.channel - это экземпляр TelegramChannel
                    # его поле channel_id - это фактический TG ID
                ).exists()
            except:
                return False
        return False  # Если у новости нет канала, не суперюзер не может ее менять (или другая логика)

    def has_delete_permission(self, request, obj=None):
        # Аналогично has_change_permission
        if request.user.is_superuser:
            return True
        if obj is None:
            return True  # Контролируется через get_queryset

        if obj.channel:
            try:
                return UserChannelPermission.objects.filter(
                    user=request.user,
                    channel__channel_id=obj.channel.channel_id
                ).exists()
            except:
                return False
        return False

    def ai_text_short(self, obj):
        if obj.ai_text:
            return (obj.ai_text[:75] + '...') if len(obj.ai_text) > 75 else obj.ai_text
        return "-"

    ai_text_short.short_description = 'AI Text'

    def image_preview(self, obj):
        if obj.image:
            import base64
            img_base64 = base64.b64encode(obj.image).decode()
            return mark_safe(f'<img src="data:image/jpeg;base64,{img_base64}" width="150" />')
        return "-"

    image_preview.short_description = 'Image'

    def publish_view(self, request, pk):
        # self.model здесь будет PostNews, так как PostNewsAdmin зарегистрирован с PostNews
        obj = self.model.objects.get(pk=pk)

        if request.method == 'POST':
            form = PublishForm(request.POST)  # PublishForm остается той же
            if form.is_valid():
                post_time_data = form.cleaned_data['post_time']
                # Django >=4.0 DateTimeField/TimeField/DateField с `null=True` возвращают None если пусто,
                # а не пустую строку, так что `or timezone.now()` должно работать.
                # Для старых версий или если поле не null=True, может потребоваться проверка.
                obj.post_time = post_time_data if post_time_data else timezone.now()
                obj.is_post = True
                obj.save()
                self.message_user(request, f'Новость ID {obj.id} (news_id: {obj.news_id}) опубликована.')
                # URL должен соответствовать новому имени модели 'postnews'
                # Имя приложения 'news' предполагается, измените если ваше другое
                return redirect(f'/admin/news/postnews/')  # ИЛИ используйте reverse
        else:
            form = PublishForm(
                initial={'post_time': obj.post_time or timezone.now()})  # Используем существующее время или текущее

        context = {
            'form': form,
            'obj': obj,
            'title': f'Опубликовать новость ID {obj.id} (news_id: {obj.news_id})',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return render(request, 'admin/publish_form.html', context)  # Шаблон может остаться тем же

    def action_buttons(self, obj):
        # Важно: URL-ы должны теперь указывать на 'postnews' вместо 'hockeynews'
        # Лучше использовать reverse для генерации URL, чтобы избежать хардкода
        # from django.urls import reverse
        # change_url = reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', args=[obj.pk])
        # publish_url = reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}-publish', args=[obj.pk]) # Для кастомного URL
        # skip_url = f'?skip={obj.pk}' # Этот остается относительным

        # Пока что оставим с хардкодом, но замените 'news/hockeynews' на 'news/postnews'
        # (или app_label/model_name вашего нового приложения/модели)
        # Предполагая, что app_label='news' и model_name='postnews'
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        return mark_safe(f'''
            <a class="button" href="/admin/{app_label}/{model_name}/{obj.pk}/change/">✏️</a>
            <a class="button" href="/admin/{app_label}/{model_name}/publish/{obj.pk}/">📤</a>
            <a class="button" href="?skip={obj.pk}">⛔</a>
        ''')

    action_buttons.short_description = 'Действия'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        # Имя URL должно быть уникальным и отражать новую модель
        # Например, 'postnews-publish'
        custom_urls = [
            path('publish/<int:pk>/', self.admin_site.admin_view(self.publish_view),
                 name=f'{self.model._meta.model_name}-publish'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Логика для 'publish' и 'skip' GET параметров
        # self.model здесь будет PostNews
        if 'publish' in request.GET:
            # Используйте try-except для обработки случая, когда объект не найден
            try:
                obj_pk = request.GET['publish']
                obj = self.model.objects.get(pk=obj_pk)
                obj.is_post = True
                obj.post_time = obj.post_time or timezone.now()  # Публикуем сейчас, если время не было установлено
                obj.save()
                messages.success(request, f'Новость ID {obj.id} (news_id: {obj.news_id}) отмечена как опубликованная.')
            except self.model.DoesNotExist:
                messages.error(request, f'Новость с PK {obj_pk} не найдена.')
            return HttpResponseRedirect(request.path.split('?')[0])  # Убираем GET параметры из URL для редиректа

        if 'skip' in request.GET:
            try:
                obj_pk = request.GET['skip']
                obj = self.model.objects.get(pk=obj_pk)
                obj.is_post = True  # или отдельное поле is_skipped, если есть
                # При пропуске, возможно, не стоит менять post_time или ставить его в далекое будущее/прошлое
                obj.save()
                messages.warning(request, f'Новость ID {obj.id} (news_id: {obj.news_id}) пропущена.')
            except self.model.DoesNotExist:
                messages.error(request, f'Новость с PK {obj_pk} не найдена.')
            return HttpResponseRedirect(request.path.split('?')[0])

        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        # obj здесь экземпляр PostNews
        obj.save()

    def delete_model(self, request, obj):
        # obj здесь экземпляр PostNews
        obj.delete()


# Регистрация новой модели и ее админ-класса
admin.site.register(PostNews, PostNewsAdmin)
print("PostNewsAdmin registered")


# Также зарегистрируйте TelegramChannel, чтобы управлять каналами через админку
@admin.register(TelegramChannel)
class TelegramChannelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'channel_id')  # channel_id здесь фактический TG ID
    search_fields = ('name', 'channel_id')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        try:
            # Показываем только те каналы, к которым у пользователя есть разрешение
            # Мы фильтруем сами TelegramChannel по их полю channel_id
            allowed_channel_tg_ids = UserChannelPermission.objects \
                .filter(user=request.user) \
                .values_list('channel__channel_id', flat=True)
            return qs.filter(channel_id__in=list(allowed_channel_tg_ids))
        except Exception as e:
            print(f"Ошибка при получении разрешенных TelegramChannel: {e}")
            return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser  # Только суперюзер может добавлять новые каналы

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True  # Контролируется get_queryset

        # Пользователь может менять канал, если он ему разрешен
        try:
            return UserChannelPermission.objects.filter(
                user=request.user,
                channel__channel_id=obj.channel_id  # obj.channel_id - это фактический TG ID канала
            ).exists()
        except:
            return False

    def has_delete_permission(self, request, obj=None):
        # Аналогично has_change_permission
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        try:
            return UserChannelPermission.objects.filter(
                user=request.user,
                channel__channel_id=obj.channel_id
            ).exists()
        except:
            return False

    # save_model, delete_model если используете 'bot_db'
    def save_model(self, request, obj, form, change):
        obj.save()

    def delete_model(self, request, obj):
        obj.delete()

