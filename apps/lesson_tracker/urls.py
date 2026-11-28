
from django.urls import path
from . import views


urlpatterns = [
    # Главная страница трекера
    path(
        '',
        views.index,
        name='lesson_tracker',
    ),

    # Импорт Excel / CSV
    path(
        'import/',
        views.import_file,
        name='lesson_tracker_import',
    ),

    # Выбор столбца с фамилиями учеников
    path(
        'import/select-column/',
        views.select_column,
        name='lesson_tracker_select_column',
    ),

    # Подтверждение импорта
    path(
        'import/confirm/',
        views.confirm_import,
        name='lesson_tracker_confirm_import',
    ),

    # Отмена импорта
    path(
        'import/cancel/',
        views.cancel_import,
        name='lesson_tracker_cancel_import',
    ),

    # Добавление балла ученику
    path(
        'student/<int:student_id>/add-point/',
        views.add_point,
        name='lesson_tracker_add_point',
    ),

    # Отмена последнего действия
    path(
        'undo/',
        views.undo,
        name='lesson_tracker_undo',
    ),

    # Сброс баллов
    path(
        'reset/',
        views.reset,
        name='lesson_tracker_reset',
    ),

    # Очистка класса
    path(
        'clear/',
        views.clear_class,
        name='lesson_tracker_clear',
    ),

    # Настройки ЕГЭ
    path(
        'update-ee/',
        views.update_ee,
        name='lesson_tracker_update_ee',
    ),

    # Завершение урока
    path(
        'finish/',
        views.finish_lesson,
        name='lesson_tracker_finish',
    ),

    # Экспорт текущего урока
    path(
        'export/',
        views.export_excel,
        name='lesson_tracker_export',
    ),

    # Экспорт сохранённого урока
    path(
        'saved/<int:lesson_id>/export/',
        views.export_saved_lesson,
        name='lesson_tracker_export_saved',
    ),

    # Экспорт всех уроков за день
    path(
        'export-day/',
        views.export_day_excel,
        name='lesson_tracker_export_day',
    ),

    # Удаление сохранённого урока
    path(
        'saved/<int:lesson_id>/delete/',
        views.delete_saved_lesson,
        name='lesson_tracker_delete_saved',
    ),
]
