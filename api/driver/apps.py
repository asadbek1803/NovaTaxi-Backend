from django.apps import AppConfig


class DriverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.driver'
    label = 'api_driver'
    verbose_name = 'Driver API'
