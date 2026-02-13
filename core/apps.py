from django.apps import AppConfig


class CoreConfig(AppConfig):
    # Mantém compatibilidade com migrações existentes (evita ALTER em PKs)
    default_auto_field = 'django.db.models.AutoField'
    name = 'core'
