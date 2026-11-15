from django.db.models import QuerySet
from django.core.exceptions import ValidationError

from core.utils import normalize_class_str, normalize_text
from .models import CardAssignment, Privilege, PrivilegeRequest
from users.models import Subject, User

MATH_JUNIOR_ONLY = {'Математика'}
MATH_SENIOR_ONLY = {'Алгебра', 'Геометрия', 'Вероятность и статистика'}


def validate_subject_for_grade(subject: Subject, grade_num: int) -> None:
    """Проверяет соответствие предмета классу и формирует подробную инструкцию для ученика."""
    if grade_num < 7 and subject.name in MATH_SENIOR_ONLY:
        raise ValidationError(
            f'Предмет «{subject.name}» изучается только с 7 класса. '
            f'Поскольку вы учитесь в {grade_num} классе, пожалуйста, выберите предмет «Математика».'
        )
    if grade_num >= 7 and subject.name in MATH_JUNIOR_ONLY:
        raise ValidationError(
            f'Предмет «{subject.name}» предназначен только для 5–6 классов. '
            f'Поскольку вы учитесь в {grade_num} классе, пожалуйста, укажите «Алгебра», «Геометрия» или «Вероятность и статистика».'
        )



def authenticate_student_card(full_name: str, class_str: str) -> CardAssignment | None:
    """Ищет активную карту ученика в текущем триместре по нормализованным ФИО и классу."""
    norm_name = normalize_text(full_name)
    norm_class = normalize_class_str(class_str)
    if not norm_name or not norm_class:
        return None

    return (
        CardAssignment.objects.select_related('student', 'trimester')
        .filter(
            trimester__is_active=True,
            student__normalized_name=norm_name,
            student__normalized_class=norm_class,
        )
        .first()
    )


def get_available_privileges_for_card(card: CardAssignment) -> list[dict]:
    """Формирует список всех привилегий с пометкой об их доступности для конкретной карты."""
    privileges = Privilege.objects.all()
    active_requests = PrivilegeRequest.objects.filter(card=card).exclude(
        status=PrivilegeRequest.Status.REJECTED
    )
    used_codes = set(active_requests.values_list('privilege__code', flat=True))

    result = []
    for priv in privileges:
        is_available = True
        unavailable_reason = ''

        if priv.code == Privilege.Code.SKIP_PRACTICE and not (
            7 <= card.student.grade_num <= 10
        ):
            is_available = False
            unavailable_reason = 'Доступно только для 7–10 классов'

        elif priv.code == Privilege.Code.DROP_GRADE:
            if card.grade_removal_used_count >= 2:
                is_available = False
                unavailable_reason = 'Использовано 2 из 2 раз'
            elif card.grade_removal_credits == 0 and card.remaining_limit == 0:
                is_available = False
                unavailable_reason = 'Закончился лимит карты'

        else:
            if priv.code in used_codes:
                is_available = False
                unavailable_reason = 'Уже использовано в этом триместре'
            elif card.remaining_limit == 0:
                is_available = False
                unavailable_reason = 'Закончился лимит карты'

        result.append(
            {
                'privilege': priv,
                'is_available': is_available,
                'unavailable_reason': unavailable_reason,
            }
        )

    return result


def get_teachers_catalog() -> list[dict]:
    """Возвращает список всех учителей, их корпусами и предметами для безопасной передачи в шаблон."""
    teachers = (
        User.objects.filter(
            is_student=False,
            is_head_teacher=False,
            is_superuser=False,
            is_active=True,
        )
        .prefetch_related('corpuses', 'subjects')
        .order_by('last_name', 'first_name')
    )
    return [
        {
            'id': t.id,
            'name': t.get_full_name() or t.username,
            'corpuses': list(t.corpuses.values_list('id', flat=True)),
            'subjects': list(t.subjects.values_list('id', flat=True)),
        }
        for t in teachers
    ]


def get_teacher_requests(user: User) -> QuerySet[PrivilegeRequest]:
    """Возвращает заявки активного триместра, адресованные лично текущему учителю."""
    return (
        PrivilegeRequest.objects.select_related(
            'card__student', 'privilege', 'subject', 'corpus'
        )
        .filter(
            card__trimester__is_active=True,
            privilege__requires_subject=True,
            teacher=user,
        )
        .order_by('status', '-created_at')
    )


def get_head_teacher_requests() -> QuerySet[PrivilegeRequest]:
    """Возвращает беспредметные заявки (№1 и №6) активного триместра для завуча."""
    return (
        PrivilegeRequest.objects.select_related('card__student', 'privilege')
        .filter(
            card__trimester__is_active=True,
            privilege__requires_subject=False,
        )
        .order_by('status', '-created_at')
    )
