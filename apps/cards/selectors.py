from django.db.models import QuerySet

from core.utils import normalize_class_str, normalize_text
from users.models import User
from .models import CardAssignment, Privilege, PrivilegeRequest


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


def get_teacher_requests(user: User) -> QuerySet[PrivilegeRequest]:
    """Возвращает заявки активного триместра строго по предметам текущего учителя."""
    return (
        PrivilegeRequest.objects.select_related('card__student', 'privilege', 'subject')
        .filter(
            card__trimester__is_active=True,
            privilege__requires_subject=True,
            subject__in=user.subjects.all(),
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
