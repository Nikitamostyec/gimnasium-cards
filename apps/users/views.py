from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import StaffLoginForm, StudentRegisterForm, TeacherRegisterForm
from .models import User


class StaffLoginView(LoginView):
    """Обрабатывает вход сотрудников и перенаправляет их в соответствующий кабинет."""

    template_name = 'users/login.html'
    authentication_form = StaffLoginForm
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        user = self.request.user
        if user.is_student:
            return reverse_lazy('cards:student_dashboard')
        if user.is_head_teacher or user.is_superuser:
            return reverse_lazy('cards:head_dashboard')
        return reverse_lazy('cards:teacher_dashboard')


class StaffLogoutView(LogoutView):
    """Завершает сессию пользователя и перенаправляет на главную страницу."""

    next_page = reverse_lazy('cards:student_login')


class StudentRegisterView(FormView):
    """Свободная самостоятельная регистрация ученика."""

    template_name = 'users/student_register.html'
    form_class = StudentRegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('cards:student_dashboard')
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
        )
        login(self.request, user)
        messages.success(self.request, 'Регистрация прошла успешно! Добро пожаловать в личный кабинет.')
        return redirect('cards:student_dashboard')


class TeacherRegisterView(FormView):
    """Самостоятельная регистрация учителя по секретному коду школы."""

    template_name = 'users/teacher_register.html'
    form_class = TeacherRegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('cards:teacher_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            first_name=form.cleaned_data['first_name'].strip(),
            last_name=form.cleaned_data['last_name'].strip(),
            is_student=False,
            is_head_teacher=False,
        )
        user.subjects.set(form.cleaned_data['subjects'])
        login(self.request, user)
        messages.success(self.request, 'Аккаунт учителя создан! Вы вошли в свой рабочий кабинет.')
        return redirect('cards:teacher_dashboard')
