from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Конфигурация приложения управления учителями, завучами и предметами."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Сотрудники и предметы'
