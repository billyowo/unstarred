from django.apps import AppConfig
from .views import start_watching


class WatcherConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "watcher"
    
    def ready(self):
        start_watching()