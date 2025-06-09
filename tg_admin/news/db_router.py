class BotDBRouter:
    def db_for_read(self, model, **hints):
        return None  # использовать default

    def db_for_write(self, model, **hints):
        return None  # использовать default

    def allow_relation(self, obj1, obj2, **hints):
        return True  # или None, если хотите дефолтное поведение

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True  # разрешить миграции во всех базах