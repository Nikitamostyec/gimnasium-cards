from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Конфигурация приложения импорта и отчетности."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'Отчеты и импорт списков'
