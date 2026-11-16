import threading
from datetime import date, timedelta


from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .selectors import validate_subject_for_grade

from users.models import Corpus, Subject, User
from .models import CardAssignment, Privilege, PrivilegeRequest


def _send_notification_async(subject: str, message: str, recipient_email: str) -> None:
    """Отправляет email в фоновом потоке, чтобы не замедлять ответ пользователю."""
    def _send():
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@gim16.ru'),
                recipient_list=[recipient_email],
                fail_silently=True,
            )
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


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
            if not user.is_superuser:
                if req.teacher_id and req.teacher_id != user.id:
                    raise PermissionDenied(
                        'Эта заявка адресована другому учителю-предметнику.'
                    )
                if not user.subjects.filter(id=req.subject_id).exists():
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
        corpus_id: int | None = None,
        subject_id: int | None = None,
        teacher_id: int | None = None,
        target_date: date | None = None,
        grade_to_remove: int | None = None,
    ) -> PrivilegeRequest:
        """Создает заявку ученика, проверяя правила, корпус, учителя и лимиты."""
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
            if not corpus_id or not Corpus.objects.filter(id=corpus_id).exists():
                raise ValidationError('Необходимо выбрать учебный корпус.')
            subject_obj = Subject.objects.filter(id=subject_id).first() if subject_id else None
            if not subject_obj:
                raise ValidationError('Необходимо выбрать корректный предмет.')
            validate_subject_for_grade(subject_obj, card.student.grade_num)
            if not teacher_id:
                raise ValidationError('Необходимо выбрать учителя-предметника.')

            teacher = User.objects.filter(
                id=teacher_id,
                is_student=False,
                is_head_teacher=False,
                is_active=True,
                corpuses__id=corpus_id,
                subjects__id=subject_id,
            ).first()
            if not teacher:
                raise ValidationError(
                    'Выбранный учитель не ведёт данный предмет в указанном корпусе.'
                )

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

        new_request = PrivilegeRequest.objects.create(
            card=card,
            privilege=privilege,
            corpus_id=corpus_id if privilege.requires_subject else None,
            subject_id=subject_id if privilege.requires_subject else None,
            teacher_id=teacher_id if privilege.requires_subject else None,
            target_date=target_date if privilege.requires_date else None,
            spent_from_reserve=spent_from_reserve,
            grade_to_remove=(
                grade_to_remove if privilege.code == Privilege.Code.DROP_GRADE else None
            ),
        )

        # Отправляем уведомление учителю после сохранения транзакции
        if new_request.teacher and new_request.teacher.email:
            student_info = (
                f'{card.student.full_name} '
                f'({card.student.grade_num}{card.student.grade_letter})'
            )
            corpus_name = new_request.corpus.name if new_request.corpus else 'Не указан'
            subject_name = new_request.subject.name if new_request.subject else 'Не указан'

            mail_subject = f'Новая заявка по карте привилегий от ученика {student_info}'
            mail_body = (
                f'Здравствуйте, {new_request.teacher.get_full_name() or new_request.teacher.username}!\n\n'
                f'Ученик {student_info} отправил вам новую заявку на использование карты привилегий.\n\n'
                f'• Привилегия: {privilege.name}\n'
                f'• Корпус: {corpus_name}\n'
                f'• Предмет: {subject_name}\n'
                f'• Номер заявки: #{new_request.pk}\n\n'
                f'Пожалуйста, зайдите в ваш личный кабинет на портале Гимназии № 16, чтобы рассмотреть заявку.'
            )
            transaction.on_commit(
                lambda: _send_notification_async(
                    mail_subject, mail_body, new_request.teacher.email
                )
            )

        return new_request

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

    @staticmethod
    def _refund_card_balance(card: CardAssignment, req: PrivilegeRequest) -> None:
        """Возвращает списанный лимит на карту ученика (с учётом пакета 2x1 для отказа от оценки)."""
        if req.privilege.code == Privilege.Code.DROP_GRADE:
            if card.grade_removal_used_count > 0:
                card.grade_removal_used_count -= 1
            if not req.spent_from_reserve and card.used > 0:
                card.used -= 1
            card.save(update_fields=['used', 'grade_removal_used_count'])
        else:
            if card.used > 0:
                card.used -= 1
                card.save(update_fields=['used'])


    @classmethod
    def process_stale_requests(cls) -> dict[str, int]:
        """Автоматически закрывает просроченные заявки с возвратом лимита и напоминает о зависших."""
        today = timezone.localdate()
        now = timezone.now()
        expired_count = 0
        reminded_count = 0

        overdue_date_qs = PrivilegeRequest.objects.select_related(
            'card', 'card__student', 'privilege'
        ).filter(
            status__in=[
                PrivilegeRequest.Status.NEW,
                PrivilegeRequest.Status.IN_PROGRESS,
            ],
            target_date__lt=today,
        )

        for req in overdue_date_qs:
            with transaction.atomic():
                locked_req = (
                    PrivilegeRequest.objects.select_for_update()
                    .select_related('card', 'privilege')
                    .get(id=req.id)
                )
                if locked_req.status not in (
                    PrivilegeRequest.Status.NEW,
                    PrivilegeRequest.Status.IN_PROGRESS,
                ):
                    continue

                card = CardAssignment.objects.select_for_update().get(
                    id=locked_req.card_id
                )
                cls._refund_card_balance(card, locked_req)

                locked_req.status = PrivilegeRequest.Status.REJECTED
                locked_req.rejection_reason = (
                    'Автоматическая отмена: выбранная дата уже прошла без рассмотрения. '
                    'Балл возвращён на вашу карту.'
                )
                locked_req.save(update_fields=['status', 'rejection_reason', 'updated_at'])
                expired_count += 1

        stale_7_days_qs = PrivilegeRequest.objects.select_related(
            'card', 'privilege'
        ).filter(
            status=PrivilegeRequest.Status.NEW,
            target_date__isnull=True,
            created_at__lt=now - timedelta(days=7),
        )

        for req in stale_7_days_qs:
            with transaction.atomic():
                locked_req = (
                    PrivilegeRequest.objects.select_for_update()
                    .select_related('card', 'privilege')
                    .get(id=req.id)
                )
                if locked_req.status != PrivilegeRequest.Status.NEW:
                    continue

                card = CardAssignment.objects.select_for_update().get(
                    id=locked_req.card_id
                )
                cls._refund_card_balance(card, locked_req)

                locked_req.status = PrivilegeRequest.Status.REJECTED
                locked_req.rejection_reason = (
                    'Автоматическая отмена: заявка не была рассмотрена в течение 7 дней. '
                    'Балл возвращён на вашу карту.'
                )
                locked_req.save(update_fields=['status', 'rejection_reason', 'updated_at'])
                expired_count += 1

        remind_qs = PrivilegeRequest.objects.select_related(
            'card__student', 'privilege', 'subject', 'teacher'
        ).filter(
            status=PrivilegeRequest.Status.NEW,
            created_at__lte=now - timedelta(days=3),
            created_at__gt=now - timedelta(days=4),
            teacher__isnull=False,
        )

        for req in remind_qs:
            if req.teacher and req.teacher.email:
                subject_line = (
                    f'Напоминание: заявка #{req.id} от {req.card.student.full_name} ожидает ответа'
                )
                body = (
                    f'Здравствуйте, {req.teacher.get_full_name() or req.teacher.username}!\n\n'
                    f'Заявка #{req.id} от ученика {req.card.student.full_name} '
                    f'({req.card.student.grade_num}{req.card.student.grade_letter} класс) '
                    f'на привилегию «{req.privilege.name}» ожидает вашего решения уже более 3 дней.\n'
                    f'Через 7 дней после подачи нерассмотренная заявка будет автоматически отменена с возвратом балла ученику.\n\n'
                    f'Перейти в кабинет: http://127.0.0'
                )
                _send_notification_async(subject_line, body, req.teacher.email)
                reminded_count += 1

        return {'expired': expired_count, 'reminded': reminded_count}
