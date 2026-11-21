from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Corpus(models.Model):
    """Учебный корпус гимназии (Вектор, Интерес, Лицей, Черёмухино)."""

    name = models.CharField('Название корпуса', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Корпус'
        verbose_name_plural = 'Корпуса'
        ordering = ['name']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Учебный предмет гимназии, к которому привязываются учителя и заявки."""

    name = models.CharField('Название предмета', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Единая модель пользователя гимназии (ученик, учитель-предметник или завуч)."""

    is_student = models.BooleanField('Ученик', default=False)
    is_head_teacher = models.BooleanField('Завуч (Администратор)', default=False)
    corpuses = models.ManyToManyField(
        Corpus,
        verbose_name='Учебные корпуса',
        blank=True,
    )
    subjects = models.ManyToManyField(
        Subject,
        verbose_name='Преподаваемые предметы',
        blank=True,
    )
    grade_num = models.PositiveSmallIntegerField(
        'Номер класса (для ученика)',
        null=True,
        blank=True,
    )
    grade_letter = models.CharField(
        'Буква класса (для ученика)',
        max_length=5,
        blank=True,
        default='',
    )
    failed_code_attempts = models.PositiveSmallIntegerField(
        'Неудачных попыток ввода кода карты',
        default=0,
    )
    code_locked_until = models.DateTimeField(
        'Блокировка ввода кода до',
        null=True,
        blank=True,
    )
    is_consent_given = models.BooleanField(
        'Согласие на обработку ПДн получено',
        default=False,
    )
    consent_date = models.DateTimeField(
        'Дата и время согласия на обработку ПДн',
        null=True,
        blank=True,
    )


    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    @property
    def is_code_locked(self) -> bool:
        if self.code_locked_until and timezone.now() < self.code_locked_until:
            return True
        return False

    def register_failed_code_attempt(self) -> None:
        self.failed_code_attempts += 1
        if self.failed_code_attempts >= 5:
            self.code_locked_until = timezone.now() + timedelta(minutes=1)
        self.save(update_fields=['failed_code_attempts', 'code_locked_until'])

    def reset_code_attempts(self) -> None:
        if self.failed_code_attempts > 0 or self.code_locked_until is not None:
            self.failed_code_attempts = 0
            self.code_locked_until = None
            self.save(update_fields=['failed_code_attempts', 'code_locked_until'])

    def __str__(self):
        full_name = self.get_full_name()
        if self.is_student and self.grade_num:
            return f'{full_name or self.username} ({self.grade_num}{self.grade_letter})'
        return full_name if full_name else self.username
