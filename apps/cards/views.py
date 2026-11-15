from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
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
    get_teachers_catalog,
)
from .services import RequestService


class StudentLoginView(LoginView):
    """Вход строго для учеников. Учителям и завучам вход через эту форму запрещён (403)."""

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

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_student:
            raise PermissionDenied('Вход на этой странице разрешён только ученикам.')
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy('cards:student_dashboard')


class StudentLogoutView(LogoutView):
    """Завершает сессию ученика строго по POST-запросу (GET запрещён -> 403)."""

    next_page = reverse_lazy('cards:student_login')

    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            raise PermissionDenied('Прямой переход по ссылке выхода запрещён.')
        return super().dispatch(request, *args, **kwargs)


class StudentActivateCardView(StudentRequiredMixin, View):
    """Привязывает карту привилегий к аккаунту ученика по секретному коду от завуча."""

    def get(self, request, *args, **kwargs):
        raise PermissionDenied('Прямой доступ к активации карты запрещён.')

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.is_code_locked:
            messages.error(
                request,
                'Слишком много неверных попыток ввода кода. Попробуйте через 1 минуту.',
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
        context['teachers_catalog_json'] = get_teachers_catalog()

        if card:
            context['privileges_info'] = get_available_privileges_for_card(card)
            context['requests'] = (
                PrivilegeRequest.objects.select_related(
                    'privilege', 'subject', 'teacher', 'corpus'
                )
                .filter(card=card)
                .order_by('-created_at')
            )
            selected_code = self.request.GET.get('privilege')
            if selected_code:
                selected_priv = Privilege.objects.filter(code=selected_code).first()
                if selected_priv:
                    context['selected_privilege'] = selected_priv
                    context['form'] = CreatePrivilegeRequestForm(
                        initial={'privilege_code': selected_priv.code},
                        grade_num=card.student.grade_num,
                    )
        return context


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """Личный кабинет ученика с жёсткой проверкой доступа к параметрам формы."""

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
        context['teachers_catalog'] = get_teachers_catalog()

        selected_code = self.request.GET.get('privilege')
        if selected_code and not card:
            raise PermissionDenied('У вас нет активной карты для оформления заявок.')

        if card:
            privileges_info = get_available_privileges_for_card(card)
            context['privileges_info'] = privileges_info
            context['requests'] = (
                PrivilegeRequest.objects.select_related(
                    'privilege', 'subject', 'teacher', 'corpus'
                )
                .filter(card=card)
                .order_by('-created_at')
            )

            if selected_code:
                available_map = {
                    item['privilege'].code: item
                    for item in privileges_info
                }
                priv_entry = available_map.get(selected_code)
                if not priv_entry or not priv_entry['is_available']:
                    raise PermissionDenied('Доступ к форме этой привилегии запрещён.')

                selected_priv = priv_entry['privilege']
                context['selected_privilege'] = selected_priv
                context['form'] = CreatePrivilegeRequestForm(
                    initial={'privilege_code': selected_priv.code}
                )
        return context


class StudentCreateRequestView(StudentRequiredMixin, View):
    """Создает заявку строго при наличии активной карты и прав на выбранную привилегию."""

    def get(self, request, *args, **kwargs):
        raise PermissionDenied('Прямой доступ к обработчику заявок запрещён.')

    def post(self, request, *args, **kwargs):
        student_profile = getattr(request.user, 'student_profile', None)
        card = (
            CardAssignment.objects.select_related('student', 'trimester')
            .filter(student=student_profile, trimester__is_active=True)
            .first()
            if student_profile
            else None
        )
        if not card:
            raise PermissionDenied('У вас нет активной карты привилегий.')

        form = CreatePrivilegeRequestForm(request.POST, grade_num=card.student.grade_num)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect('cards:student_dashboard')

        privilege_code = form.cleaned_data['privilege_code']
        available_map = {
            item['privilege'].code: item['is_available']
            for item in get_available_privileges_for_card(card)
        }
        if not available_map.get(privilege_code, False):
            raise PermissionDenied('Попытка отправить заявку на недоступную привилегию.')

        corpus = form.cleaned_data.get('corpus')
        subject = form.cleaned_data.get('subject')
        teacher = form.cleaned_data.get('teacher')
        try:
            RequestService.create_request(
                card_id=card.id,
                privilege_code=privilege_code,
                corpus_id=corpus.id if corpus else None,
                subject_id=subject.id if subject else None,
                teacher_id=teacher.id if teacher else None,
                target_date=form.cleaned_data.get('target_date'),
                grade_to_remove=form.cleaned_data.get('grade_to_remove'),
            )
            messages.success(request, 'Заявка успешно отправлена!')
        except ValidationError as exc:
            messages.error(request, exc.message)

        return redirect('cards:student_dashboard')


class StudentRequestFormPartialView(StudentRequiredMixin, View):
    """Отдаёт HTMX-фрагмент формы строго по внутреннему HTMX-запросу и при наличии прав."""

    def get(self, request, code: str, *args, **kwargs):
        if request.headers.get('HX-Request') != 'true':
            raise PermissionDenied('Прямой доступ к фрагменту формы запрещён.')

        student_profile = getattr(request.user, 'student_profile', None)
        card = (
            CardAssignment.objects.select_related('student', 'trimester')
            .filter(student=student_profile, trimester__is_active=True)
            .first()
            if student_profile
            else None
        )
        if not card:
            raise PermissionDenied('У вас нет активной карты на текущий триместр.')

        privilege = get_object_or_404(Privilege, code=code)

        available_map = {
            item['privilege'].code: item['is_available']
            for item in get_available_privileges_for_card(card)
        }
        if not available_map.get(privilege.code, False):
            raise PermissionDenied('Эта привилегия недоступна для вашей карты.')

        form = CreatePrivilegeRequestForm(
            initial={'privilege_code': privilege.code},
            grade_num=card.student.grade_num,
        )

        return render(
            request,
            'student/partials/_request_form.html',
            {
                'privilege': privilege,
                'form': form,
                'teachers_catalog': get_teachers_catalog(),
            },
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

    def get(self, request, *args, **kwargs):
        raise PermissionDenied('Прямой доступ к изменению статуса заявки запрещён.')

    def post(self, request, pk: int, action: str, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active or request.user.is_student:
            raise PermissionDenied('Доступ запрещён.')

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
                raise Http404('Неизвестное действие.')
        except PrivilegeRequest.DoesNotExist as exc:
            raise Http404('Заявка не найдена.') from exc
        except ValidationError as exc:
            messages.error(request, exc.message)

        return redirect(redirect_url)
