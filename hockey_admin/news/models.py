from django.db import models


# class News(models.Model):
#     title = models.CharField(max_length=255)
#     content = models.TextField()
#     image_url = models.URLField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return self.title
#
#     class Meta:
#         verbose_name = "Круги вбрасывания | PUPKOV"
#         verbose_name_plural = "Новости"

class HockeyNews(models.Model):
    news_id = models.IntegerField(unique=True)
    pars_text = models.TextField()
    ai_text = models.TextField()
    url_image = models.URLField(blank=True, null=True)
    image = models.BinaryField(blank=True, null=True)
    is_post = models.BooleanField(default=False)
    post_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'post_hockey_news'
        app_label = 'news'
        default_permissions = ()
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'