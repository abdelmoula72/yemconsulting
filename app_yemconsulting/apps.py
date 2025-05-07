from django.apps import AppConfig

# Configuration de l'application app_yemconsulting
class AppYemconsultingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_yemconsulting'

    def ready(self):
        import app_yemconsulting.signals

