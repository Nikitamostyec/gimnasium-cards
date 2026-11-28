from django.db import models


class SavedLesson(models.Model):
    teacher_code = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name='ID учителя',
    )
    title = models.CharField(
        max_length=120,
        verbose_name='Название урока',
    )
    lesson_date = models.DateField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата урока',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время сохранения',
    )
    results_json = models.JSONField(
        default=list,
        verbose_name='Результаты урока',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сохранённый урок'
        verbose_name_plural = 'Сохранённые уроки'

    def __str__(self):
        return self.title
