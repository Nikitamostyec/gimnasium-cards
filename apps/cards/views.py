from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from core.mixins import (
    HeadTeacherRequiredMixin,
    StudentRequiredMixin,
    TeacherRequiredMixin,
)
from .forms import (
    ActivateCardForm,
    CreatePrivilegeRequestForm,
    RejectRequestForm,
    StudentAccountLoginForm,
)
from .models import CardAssignment, Privilege, PrivilegeRequest, Student
from .selectors import (
    get_available_privileges_for_card,
    get_head_teacher_requests,
    get_teacher_requests,
)
from .services import RequestService


class StudentLoginView(LoginView):
    """Вход ученика по логину и паролю."""

    template_name = 'student/login.html'
    authentication_form = StudentAccountLoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_student:
                return redirect('cards:student_dashboard')
            if request.user.is_head_teacher or request.user.is_superuser:
                return redirect('cards:head_dashboard')
            return redirect('cards:teacher_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self) -> str:
        user = self.request.user
        if not user.is_student:
            if user.is_head_teacher or user.is_superuser:
                return reverse_lazy('cards:head_dashboard')
            return reverse_lazy('cards:teacher_dashboard')
        return reverse_lazy('cards:student_dashboard')


class StudentLogoutView(LogoutView):
    """Завершает сессию ученика и перенаправляет на страницу входа."""

    next_page = reverse_lazy('cards:student_login')


class StudentActivateCardView(StudentRequiredMixin, View):
    """Привязывает карту привилегий к аккаунту ученика по секретному коду от завуча."""

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.is_code_locked:
            messages.error(
                request,
                'Слишком много неверных попыток ввода кода. Попробуйте через 15 минут.',
            )
            return redirect('cards:student_dashboard')

        form = ActivateCardForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Введите корректный код активации.')
            return redirect('cards:student_dashboard')

        code = form.cleaned_data['activation_code']
        student_record = Student.objects.filter(
            activation_code=code,
            user__isnull=True,
        ).first()

        if not student_record:
            user.register_failed_code_attempt()
            messages.error(
                request,
                'Неверный или уже использованный код карты. Проверьте код, выданный завучем.',
            )
            return redirect('cards:student_dashboard')

        student_record.user = user
        student_record.activation_code = ''
        student_record.save(update_fields=['user', 'activation_code'])
        user.reset_code_attempts()

        messages.success(
            request,
            f'Карта привилегий ({student_record.full_name}) успешно привязана к вашему кабинету!',
        )
        return redirect('cards:student_dashboard')


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """Личный кабинет любого ученика (с картой или без карты)."""

    template_name = 'student/dashboard.html'

    def get_active_card(self) -> CardAssignment | None:
        student_profile = getattr(self.request.user, 'student_profile', None)
        if not student_profile:
            return None
        return (
            CardAssignment.objects.select_related('student', 'trimester')
            .filter(student=student_profile, trimester__is_active=True)
            .first()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card = self.get_active_card()
        context['card'] = card
        context['activate_form'] = ActivateCardForm()

        if card:
            context['privileges_info'] = get_available_privileges_for_card(card)
            context['requests'] = (
                PrivilegeRequest.objects.select_related('privilege', 'subject')
                .filter(card=card)
                .order_by('-created_at')
            )
            selected_code = self.request.GET.get('privilege')
            if selected_code:
                selected_priv = Privilege.objects.filter(code=selected_code).first()
                if selected_priv:
                    context['selected_privilege'] = selected_priv
                    context['form'] = CreatePrivilegeRequestForm(
                        initial={'privilege_code': selected_priv.code}
                    )
        return context


class StudentCreateRequestView(StudentRequiredMixin, View):
    """Создает заявку только если у ученика есть привязанная активная карта."""

    def post(self, request, *args, **kwargs):
        student_profile = getattr(request.user, 'student_profile', None)
        card = (
            CardAssignment.objects.filter(
                student=student_profile, trimester__is_active=True
            ).first()
            if student_profile
            else None
        )
        if not card:
            messages.error(
                request,
                'У вас нет активной карты привилегий на текущий триместр.',
            )
            return redirect('cards:student_dashboard')

        form = CreatePrivilegeRequestForm(request.POST)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect('cards:student_dashboard')

        subject = form.cleaned_data.get('subject')
        try:
            RequestService.create_request(
                card_id=card.id,
                privilege_code=form.cleaned_data['privilege_code'],
                subject_id=subject.id if subject else None,
                target_date=form.cleaned_data.get('target_date'),
                grade_to_remove=form.cleaned_data.get('grade_to_remove'),
            )
            messages.success(request, 'Заявка успешно отправлена!')
        except ValidationError as exc:
            messages.error(request, exc.message)

        return redirect('cards:student_dashboard')


class StudentRequestFormPartialView(StudentRequiredMixin, View):
    """Возвращает HTMX-фрагмент формы с нужными полями под выбранную привилегию."""

    def get(self, request, code: str, *args, **kwargs):
        privilege = get_object_or_404(Privilege, code=code)
        form = CreatePrivilegeRequestForm(initial={'privilege_code': privilege.code})
        return render(
            request,
            'student/partials/_request_form.html',
            {'privilege': privilege, 'form': form},
        )


class TeacherDashboardView(TeacherRequiredMixin, TemplateView):
    """Отображает очередь заявок для учителя-предметника."""

    template_name = 'teacher/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_requests = get_teacher_requests(self.request.user)
        context['new_requests'] = all_requests.filter(
            status=PrivilegeRequest.Status.NEW
        )
        context['in_progress_requests'] = all_requests.filter(
            status=PrivilegeRequest.Status.IN_PROGRESS
        )
        context['archived_requests'] = all_requests.filter(
            status__in=[
                PrivilegeRequest.Status.COMPLETED,
                PrivilegeRequest.Status.REJECTED,
            ]
        )
        context['reject_form'] = RejectRequestForm()
        return context


class HeadTeacherDashboardView(HeadTeacherRequiredMixin, TemplateView):
    """Отображает очередь беспредметных заявок (№1 и №6) для завуча."""

    template_name = 'head_teacher/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_requests = get_head_teacher_requests()
        context['new_requests'] = all_requests.filter(
            status=PrivilegeRequest.Status.NEW
        )
        context['in_progress_requests'] = all_requests.filter(
            status=PrivilegeRequest.Status.IN_PROGRESS
        )
        context['archived_requests'] = all_requests.filter(
            status__in=[
                PrivilegeRequest.Status.COMPLETED,
                PrivilegeRequest.Status.REJECTED,
            ]
        )
        context['reject_form'] = RejectRequestForm()
        return context


class StaffChangeRequestStatusView(View):
    """Универсальный защищенный обработчик смены статуса заявки сотрудником."""

    def post(self, request, pk: int, action: str, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

        redirect_url = (
            'cards:head_dashboard'
            if (request.user.is_head_teacher or request.user.is_superuser)
            else 'cards:teacher_dashboard'
        )

        try:
            if action == 'take':
                RequestService.change_status(
                    request_id=pk,
                    user=request.user,
                    new_status=PrivilegeRequest.Status.IN_PROGRESS,
                )
                messages.info(request, f'Заявка #{pk} взята в работу.')
            elif action == 'complete':
                RequestService.change_status(
                    request_id=pk,
                    user=request.user,
                    new_status=PrivilegeRequest.Status.COMPLETED,
                )
                messages.success(request, f'Заявка #{pk} отмечена как выполненная.')
            elif action == 'reject':
                form = RejectRequestForm(request.POST)
                if not form.is_valid():
                    messages.error(request, 'Необходимо указать причину отклонения.')
                    return redirect(redirect_url)
                RequestService.reject_request(
                    request_id=pk,
                    user=request.user,
                    reason=form.cleaned_data['reason'],
                )
                messages.warning(
                    request,
                    f'Заявка #{pk} отклонена. Лимит возвращен ученику.',
                )
            else:
                raise ValidationError('Неизвестное действие.')
        except PrivilegeRequest.DoesNotExist as exc:
            raise PermissionDenied from exc
        except ValidationError as exc:
            messages.error(request, exc.message)

        return redirect(redirect_url)

