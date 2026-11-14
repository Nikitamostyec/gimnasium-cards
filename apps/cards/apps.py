from django.apps import AppConfig


class CardsConfig(AppConfig):
    """Конфигурация приложения учета карт и заявок на привилегии."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cards'
    verbose_name = 'Привилегии по картам'
