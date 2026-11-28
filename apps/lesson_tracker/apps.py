from django.apps import AppConfig


class LessonTrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.lesson_tracker'
    verbose_name = 'Журнал оценок за урок'