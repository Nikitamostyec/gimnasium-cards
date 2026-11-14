from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from users.models import Subject, User
from .models import CardAssignment, Privilege, PrivilegeRequest


class RequestService:
    """Сервис транзакционного управления заявками и лимитами карт."""

    @staticmethod
    def _validate_staff_permission(user: User, req: PrivilegeRequest) -> None:
        """Проверяет право сотрудника обрабатывать конкретную заявку."""
        if not req.card.trimester.is_active:
            raise ValidationError('Нельзя изменять заявки закрытого триместра.')

        if req.privilege.requires_subject:
            if user.is_head_teacher and not user.is_superuser:
                raise PermissionDenied(
                    'Предметные заявки обрабатываются только учителями-предметниками.'
                )
            if not user.is_superuser and not user.subjects.filter(
                id=req.subject_id
            ).exists():
                raise PermissionDenied(
                    'У вас нет прав на обработку заявок по данному предмету.'
                )
        else:
            if not user.is_head_teacher and not user.is_superuser:
                raise PermissionDenied(
                    'Беспредметные заявки обрабатываются только завучем.'
                )

    @staticmethod
    @transaction.atomic
    def create_request(
        card_id: int,
        privilege_code: str,
        subject_id: int | None = None,
        target_date: date | None = None,
        grade_to_remove: int | None = None,
    ) -> PrivilegeRequest:
        """Создает заявку ученика, проверяя правила, лимиты и блокируя запись карты."""
        card = (
            CardAssignment.objects.select_for_update()
            .select_related('student', 'trimester')
            .get(id=card_id)
        )
        privilege = Privilege.objects.get(code=privilege_code)

        if not card.trimester.is_active:
            raise ValidationError('Прием заявок в этом триместре закрыт.')

        if privilege.code == Privilege.Code.SKIP_DAY:
            if not target_date:
                raise ValidationError('Необходимо указать дату освобождения.')
            min_date = timezone.localdate() + timedelta(days=2)
            if target_date < min_date:
                raise ValidationError(
                    f'Заявку можно подать не ранее чем с {min_date.strftime("%d.%m.%Y")}.'
                )

        if privilege.code == Privilege.Code.SKIP_PRACTICE:
            if not (7 <= card.student.grade_num <= 10):
                raise ValidationError(
                    'Освобождение от практики доступно только ученикам 7–10 классов.'
                )

        if privilege.requires_subject:
            if not subject_id or not Subject.objects.filter(id=subject_id).exists():
                raise ValidationError('Необходимо выбрать корректный предмет.')

        active_requests = PrivilegeRequest.objects.filter(
            card=card,
            privilege=privilege,
        ).exclude(status=PrivilegeRequest.Status.REJECTED)

        spent_from_reserve = False

        if privilege.code == Privilege.Code.DROP_GRADE:
            if card.grade_removal_used_count >= 2:
                raise ValidationError(
                    'Право отказа от оценок уже использовано максимальное число раз (2).'
                )

            if card.grade_removal_credits > 0:
                card.grade_removal_credits -= 1
                spent_from_reserve = True
            else:
                if card.used >= card.limit:
                    raise ValidationError('У вас закончился общий лимит привилегий.')
                card.used += 1
                card.grade_removal_credits = 1
                spent_from_reserve = False

            card.grade_removal_used_count += 1
        else:
            if active_requests.exists():
                raise ValidationError(
                    'Эту привилегию можно использовать только 1 раз за триместр.'
                )

            if card.used >= card.limit:
                raise ValidationError('У вас закончился общий лимит привилегий.')

            card.used += 1

        card.save()

        return PrivilegeRequest.objects.create(
            card=card,
            privilege=privilege,
            subject_id=subject_id if privilege.requires_subject else None,
            target_date=target_date if privilege.requires_date else None,
            spent_from_reserve=spent_from_reserve,
            grade_to_remove=grade_to_remove if privilege.code == Privilege.Code.DROP_GRADE else None,

        )

    @staticmethod
    @transaction.atomic
    def change_status(request_id: int, user: User, new_status: str) -> PrivilegeRequest:
        """Переводит заявку в статус «В работе» или «Выполнено»."""
        if new_status not in (
            PrivilegeRequest.Status.IN_PROGRESS,
            PrivilegeRequest.Status.COMPLETED,
        ):
            raise ValidationError('Недопустимый статус для данного действия.')

        req = (
            PrivilegeRequest.objects.select_for_update()
            .select_related('card__trimester', 'privilege')
            .get(id=request_id)
        )
        RequestService._validate_staff_permission(user, req)

        if req.status in (
            PrivilegeRequest.Status.COMPLETED,
            PrivilegeRequest.Status.REJECTED,
        ):
            raise ValidationError('Заявка уже закрыта и не может быть изменена.')

        req.status = new_status
        req.processed_by = user
        req.save()
        return req

    @staticmethod
    @transaction.atomic
    def reject_request(request_id: int, user: User, reason: str) -> PrivilegeRequest:
        """Отклоняет заявку с указанием причины и возвращает ученику потраченный лимит."""
        if not reason or not reason.strip():
            raise ValidationError('Необходимо указать причину отклонения.')

        req = (
            PrivilegeRequest.objects.select_for_update()
            .select_related('card__trimester', 'privilege')
            .get(id=request_id)
        )
        RequestService._validate_staff_permission(user, req)

        if req.status in (
            PrivilegeRequest.Status.COMPLETED,
            PrivilegeRequest.Status.REJECTED,
        ):
            raise ValidationError('Заявка уже закрыта и не может быть отклонена.')

        card = CardAssignment.objects.select_for_update().get(id=req.card_id)

        if req.privilege.code == Privilege.Code.DROP_GRADE:
            card.grade_removal_used_count = max(0, card.grade_removal_used_count - 1)
            if req.spent_from_reserve:
                card.grade_removal_credits += 1
            else:
                if card.grade_removal_credits > 0:
                    card.grade_removal_credits -= 1
                    card.used = max(0, card.used - 1)
                else:
                    second_req = (
                        PrivilegeRequest.objects.select_for_update()
                        .filter(
                            card=card,
                            privilege=req.privilege,
                            spent_from_reserve=True,
                        )
                        .exclude(status=PrivilegeRequest.Status.REJECTED)
                        .first()
                    )
                    if second_req:
                        second_req.spent_from_reserve = False
                        second_req.save()
                    else:
                        card.used = max(0, card.used - 1)
        else:
            card.used = max(0, card.used - 1)

        card.save()

        req.status = PrivilegeRequest.Status.REJECTED
        req.rejection_reason = reason.strip()
        req.processed_by = user
        req.save()
        return req
