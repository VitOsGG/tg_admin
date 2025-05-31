from django.contrib import admin
from .models import HockeyNews
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from django import forms
from django.shortcuts import render, redirect
from django.utils import timezone


class PublishForm(forms.Form):
    post_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],  # формат для datetime-local без секунд
        label='Время публикации (оставьте пустым для текущего времени)'
    )


class HockeyNewsAdminForm(forms.ModelForm):
    image_file = forms.FileField(required=False, label='Загрузить новое фото')

    class Meta:
        model = HockeyNews
        fields = '__all__'
        widgets = {
            'post_time': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }
        exclude = ['image']

    def save(self, commit=True):
        instance = super().save(commit=False)
        file = self.cleaned_data.get('image_file')
        if file:
            instance.image = file.read()
        if commit:
            instance.save()
        return instance


class HockeyNewsAdmin(admin.ModelAdmin):
    form = HockeyNewsAdminForm
    list_display = ['news_id', 'ai_text_short', 'image_preview', 'post_time', 'is_post', 'action_buttons']
    readonly_fields = ['image_preview']
    fields = ['news_id', 'ai_text', 'url_image', 'image_preview', 'image_file', 'is_post', 'post_time']
    list_display_links = ['news_id']  # Кликаем по news_id — открываем редактирование

    def ai_text_short(self, obj):
        return (obj.ai_text[:75] + '...') if len(obj.ai_text) > 75 else obj.ai_text
    ai_text_short.short_description = 'AI Text'

    def image_preview(self, obj):
        if obj.image:
            import base64
            img_base64 = base64.b64encode(obj.image).decode()
            return mark_safe(f'<img src="data:image/jpeg;base64,{img_base64}" width="150" />')
        return "-"
    image_preview.short_description = 'Image'

    def publish_view(self, request, pk):
        obj = self.model.objects.using('bot_db').get(pk=pk)

        if request.method == 'POST':
            form = PublishForm(request.POST)
            if form.is_valid():
                post_time = form.cleaned_data['post_time'] or timezone.now()
                obj.is_post = True
                obj.post_time = post_time
                obj.save(using='bot_db')
                self.message_user(request, f'Новость {obj.news_id} опубликована.')
                return redirect(f'/admin/news/hockeynews/')
        else:
            form = PublishForm(initial={'post_time': timezone.now()})

        context = {
            'form': form,
            'obj': obj,
            'title': f'Опубликовать новость {obj.news_id}',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return render(request, 'admin/publish_form.html', context)

    def action_buttons(self, obj):
        return mark_safe(f'''
            <a class="button" href="/admin/news/hockeynews/{obj.pk}/change/">✏️</a>
            <a class="button" href="/admin/news/hockeynews/publish/{obj.pk}/">📤</a>
            <a class="button" href="?skip={obj.pk}">⛔</a>
        ''')
    action_buttons.short_description = 'Действия'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('publish/<int:pk>/', self.admin_site.admin_view(self.publish_view), name='hockeynews-publish'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if 'publish' in request.GET:
            obj = self.model.objects.using('bot_db').get(pk=request.GET['publish'])
            obj.is_post = True
            obj.save(using='bot_db')
            messages.success(request, f'Новость {obj.news_id} отмечена как опубликованная.')
            return HttpResponseRedirect(request.path)

        if 'skip' in request.GET:
            obj = self.model.objects.using('bot_db').get(pk=request.GET['skip'])
            obj.is_post = True  # или отдельное поле is_skipped
            obj.save(using='bot_db')
            messages.warning(request, f'Новость {obj.news_id} пропущена.')
            return HttpResponseRedirect(request.path)

        return super().change_view(request, object_id, form_url, extra_context)

    def get_queryset(self, request):
        return super().get_queryset(request).using('bot_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='bot_db')

    def delete_model(self, request, obj):
        obj.delete(using='bot_db')


admin.site.register(HockeyNews, HockeyNewsAdmin)