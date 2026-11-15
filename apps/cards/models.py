import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.utils import normalize_class_str, normalize_text
from users.models import Corpus, Subject


def generate_activation_code() -> str:
    """Генерирует криптостойкий 8-значный код без похожих символов (0/O, 1/I)."""
    alphabet = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    raw = ''.join(secrets.choice(alphabet) for _ in range(8))
    return f'{raw[:4]}-{raw[4:]}'


class Trimester(models.Model):
    """Учебный триместр, определяющий срок действия карт."""

    name = models.CharField('Название триместра', max_length=100)
    is_active = models.BooleanField('Активный триместр', default=False)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Триместр'
        verbose_name_plural = 'Триместры'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Обеспечивает уникальность активного триместра в системе."""
        if self.is_active:
            Trimester.objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Student(models.Model):
    """Ученик гимназии с нормализованными полями для поиска и защитой паролем."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name='Аккаунт ученика',
    )
    full_name = models.CharField('ФИО', max_length=255)
    normalized_name = models.CharField(
        'ФИО (нормализованное)',
        max_length=255,
        db_index=True,
        editable=False,
    )
    grade_num = models.PositiveSmallIntegerField('Номер класса')
    grade_letter = models.CharField('Буква класса', max_length=5)
    normalized_class = models.CharField(
        'Класс (нормализованный)',
        max_length=10,
        db_index=True,
        editable=False,
    )
    password = models.CharField(
        'Хэш пароля',
        max_length=128,
        blank=True,
        default='',
    )
    activation_code = models.CharField(
        'Код активации',
        max_length=12,
        blank=True,
        default=generate_activation_code,
    )
    failed_attempts = models.PositiveSmallIntegerField(
        'Неудачных попыток входа',
        default=0,
    )
    locked_until = models.DateTimeField(
        'Заблокирован до',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Ученик'
        verbose_name_plural = 'Ученики'
        unique_together = ('normalized_name', 'normalized_class')
        ordering = ['grade_num', 'grade_letter', 'full_name']

    @property
    def has_password(self) -> bool:
        return bool(self.password)

    @property
    def is_locked(self) -> bool:
        """Проверяет, активна ли временная блокировка от перебора."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def register_failed_attempt(self) -> None:
        """Увеличивает счетчик ошибок и блокирует аккаунт на 15 минут после 5 попыток."""
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=15)
        self.save(update_fields=['failed_attempts', 'locked_until'])

    def reset_attempts(self) -> None:
        """Сбрасывает счетчик ошибок при успешном входе."""
        if self.failed_attempts > 0 or self.locked_until is not None:
            self.failed_attempts = 0
            self.locked_until = None
            self.save(update_fields=['failed_attempts', 'locked_until'])

    def reset_access(self) -> str:
        """Сбрасывает пароль ученика и генерирует новый одноразовый код (для завуча)."""
        self.password = ''
        self.activation_code = generate_activation_code()
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=['password', 'activation_code', 'failed_attempts', 'locked_until'])
        return self.activation_code

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password:
            return False
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_text(self.full_name)
        self.grade_letter = self.grade_letter.strip().upper()
        raw_class = f'{self.grade_num}{self.grade_letter}'
        self.normalized_class = normalize_class_str(raw_class)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.full_name} ({self.grade_num}{self.grade_letter})'


class CardAssignment(models.Model):
    """Привязка золотой или серебряной карты к ученику на конкретный триместр."""

    class CardType(models.TextChoices):
        GOLD = 'GOLD', 'Золотая (3 привилегии)'
        SILVER = 'SILVER', 'Серебряная (2 привилегии)'

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='cards',
        verbose_name='Ученик',
    )
    trimester = models.ForeignKey(
        Trimester,
        on_delete=models.CASCADE,
        related_name='cards',
        verbose_name='Триместр',
    )
    card_type = models.CharField(
        'Тип карты',
        max_length=10,
        choices=CardType.choices,
    )
    limit = models.PositiveSmallIntegerField('Общий лимит', editable=False)
    used = models.PositiveSmallIntegerField('Потрачено лимитов', default=0)
    grade_removal_credits = models.PositiveSmallIntegerField(
        'Резерв для 2-го отказа от оценки',
        default=0,
    )
    grade_removal_used_count = models.PositiveSmallIntegerField(
        'Использовано отказов от оценок',
        default=0,
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Карта ученика'
        verbose_name_plural = 'Карты учеников'
        unique_together = ('student', 'trimester')

    def save(self, *args, **kwargs):
        """Устанавливает базовый лимит при создании и блокирует смену типа карты."""
        if not self.pk:
            self.limit = 3 if self.card_type == self.CardType.GOLD else 2
        else:
            old_type = (
                CardAssignment.objects.filter(pk=self.pk)
                .values_list('card_type', flat=True)
                .first()
            )
            if old_type and old_type != self.card_type:
                raise ValidationError(
                    'Тип карты не может быть изменен в течение триместра.'
                )
        super().save(*args, **kwargs)

    @property
    def remaining_limit(self) -> int:
        """Возвращает количество оставшихся основных привилегий."""
        return max(0, self.limit - self.used)

    def __str__(self):
        return f'{self.student} — {self.get_card_type_display()} ({self.trimester})'


class Privilege(models.Model):
    """Справочник доступных привилегий по картам."""

    class Code(models.TextChoices):
        SKIP_DAY = 'SKIP_DAY', '1. Освобождение от учебных занятий на 1 день'
        SKIP_TEST = 'SKIP_TEST', '2. Освобождение от написания одной контрольной работы'
        SKIP_MIN = 'SKIP_MIN', '3. Освобождение от сдачи «образовательного минимума»'
        ADD_NINE = 'ADD_NINE', '4. Выставление в журнал одной оценки «9»'
        DROP_GRADE = 'DROP_GRADE', '5. Право отказаться от текущих оценок (Пакет)'
        SKIP_PRACTICE = 'SKIP_PRACTICE', '6. Освобождение от летней трудовой практики'

    code = models.CharField('Код', max_length=20, choices=Code.choices, unique=True)
    name = models.CharField('Название', max_length=255)
    requires_subject = models.BooleanField('Требуется предмет', default=True)
    requires_date = models.BooleanField('Требуется дата', default=False)

    class Meta:
        verbose_name = 'Привилегия'
        verbose_name_plural = 'Привилегии'
        ordering = ['code']

    def __str__(self):
        return self.name


class PrivilegeRequest(models.Model):
    """Заявка ученика на использование привилегии."""

    class Status(models.TextChoices):
        NEW = 'NEW', 'Новая'
        IN_PROGRESS = 'IN_PROGRESS', 'В работе'
        COMPLETED = 'COMPLETED', 'Выполнено'
        REJECTED = 'REJECTED', 'Отклонено'

    card = models.ForeignKey(
        CardAssignment,
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name='Карта ученика',
    )
    privilege = models.ForeignKey(
        Privilege,
        on_delete=models.PROTECT,
        verbose_name='Привилегия',
    )
    corpus = models.ForeignKey(
        Corpus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Корпус',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Предмет',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='assigned_requests',
        verbose_name='Учитель-предметник',
    )
    target_date = models.DateField('Желаемая дата', null=True, blank=True)
    grade_to_remove = models.PositiveSmallIntegerField(
        'Оценка для аннулирования (1–10)',
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )

    status = models.CharField(
        'Статус',
        max_length=15,
        choices=Status.choices,
        default=Status.NEW,
    )
    rejection_reason = models.TextField('Причина отклонения', blank=True)
    spent_from_reserve = models.BooleanField(
        'Списано из резерва (для №5)',
        default=False,
    )
    created_at = models.DateTimeField('Дата подачи', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Обработал сотрудник',
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Заявка на привилегию'
        verbose_name_plural = 'Заявки на привилегии'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка #{self.pk}: {self.card.student} — {self.privilege.name}'

