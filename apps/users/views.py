from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from .forms import (
    StaffLoginForm,
    StudentRegisterForm,
    TeacherRegisterForm,
    UserProfileForm,
)
from .models import User


class StaffLoginView(LoginView):
    """Вход строго для учителей и завучей. Ученикам вход через эту форму запрещён (403)."""

    template_name = 'users/login.html'
    authentication_form = StaffLoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_student:
                raise PermissionDenied('Вы уже вошли как ученик.')
            if request.user.is_head_teacher or request.user.is_superuser:
                return redirect('cards:head_dashboard')
            return redirect('cards:teacher_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if user.is_student:
            raise PermissionDenied(
                'Вход в кабинет сотрудников разрешён только учителям и завучам.'
            )
        return super().form_valid(form)

    def get_success_url(self) -> str:
        user = self.request.user
        if user.is_head_teacher or user.is_superuser:
            return reverse_lazy('cards:head_dashboard')
        return reverse_lazy('cards:teacher_dashboard')


class StaffLogoutView(LogoutView):
    """Завершает сессию пользователя строго по POST-запросу (GET запрещён -> 403)."""

    next_page = reverse_lazy('cards:student_login')

    def get(self, request, *args, **kwargs):
        raise PermissionDenied('Прямой переход по ссылке выхода запрещён.')


class StudentRegisterView(FormView):
    """Свободная самостоятельная регистрация ученика."""

    template_name = 'users/student_register.html'
    form_class = StudentRegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            raise PermissionDenied('Регистрация недоступна для авторизованных пользователей.')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        grade_num, grade_letter = form.cleaned_data['class_str']
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            first_name=form.cleaned_data['first_name'].strip(),
            last_name=form.cleaned_data['last_name'].strip(),
            is_student=True,
            grade_num=grade_num,
            grade_letter=grade_letter,
            is_consent_given=True,
            consent_date=timezone.now(),
        )

        login(self.request, user)
        messages.success(
            self.request,
            'Регистрация прошла успешно! Добро пожаловать в личный кабинет.',
        )
        return redirect('cards:student_dashboard')


class TeacherRegisterView(FormView):
    """Самостоятельная регистрация учителя по секретному коду школы."""

    template_name = 'users/teacher_register.html'
    form_class = TeacherRegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            raise PermissionDenied('Регистрация недоступна для авторизованных пользователей.')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            first_name=form.cleaned_data['first_name'].strip(),
            last_name=form.cleaned_data['last_name'].strip(),
            email=form.cleaned_data['email'].strip(),
            is_student=False,
            is_head_teacher=False,
            is_consent_given=True,
            consent_date=timezone.now(),
        )

        user.corpuses.set(form.cleaned_data['corpuses'])
        user.subjects.set(form.cleaned_data['subjects'])

        login(self.request, user)
        messages.success(
            self.request,
            'Аккаунт учителя создан! Вы вошли в свой рабочий кабинет.',
        )
        return redirect('cards:teacher_dashboard')


class UserProfileView(LoginRequiredMixin, FormView):
    """Просмотр и редактирование личного профиля (ученик, учитель, завуч)."""

    template_name = 'users/profile.html'
    form_class = UserProfileForm
    success_url = reverse_lazy('users:profile')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_active:
            raise PermissionDenied('Учётная запись заблокирована.')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user: User = self.request.user  # type: ignore[assignment]
        user.last_name = form.cleaned_data['last_name'].strip()
        user.first_name = form.cleaned_data['first_name'].strip()

        if 'email' in form.cleaned_data:
            user.email = form.cleaned_data['email'].strip()

        if user.is_student and 'class_str' in form.cleaned_data:
            grade_num, grade_letter = form.cleaned_data['class_str']
            user.grade_num = grade_num
            user.grade_letter = grade_letter

            student_profile = getattr(user, 'student_profile', None)
            if student_profile:
                student_profile.full_name = f'{user.last_name} {user.first_name}'.strip()
                student_profile.grade_num = grade_num
                student_profile.grade_letter = grade_letter
                student_profile.save()

        if not user.is_student and not user.is_head_teacher and not user.is_superuser:
            user.corpuses.set(form.cleaned_data['corpuses'])
            user.subjects.set(form.cleaned_data['subjects'])

        new_password = form.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)

        user.save()

        if new_password:
            update_session_auth_hash(self.request, user)

        messages.success(self.request, 'Данные вашего профиля успешно обновлены!')
        return super().form_valid(form)


class PrivacyPolicyView(TemplateView):
    """Страница Политики конфиденциальности и обработки персональных данных."""

    template_name = 'users/privacy.html'
