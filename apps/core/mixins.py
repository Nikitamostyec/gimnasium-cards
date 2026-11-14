from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


class StudentRequiredMixin(AccessMixin):
    """Ограничивает доступ только для авторизованных учеников."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('cards:student_login')
        if not request.user.is_student:
            if request.user.is_head_teacher or request.user.is_superuser:
                return redirect('cards:head_dashboard')
            return redirect('cards:teacher_dashboard')
        return super().dispatch(request, *args, **kwargs)


class TeacherRequiredMixin(AccessMixin):
    """Ограничивает доступ только для авторизованных учителей-предметников."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_student:
            return redirect('cards:student_dashboard')
        if request.user.is_head_teacher and not request.user.is_superuser:
            return redirect('cards:head_dashboard')
        return super().dispatch(request, *args, **kwargs)


class HeadTeacherRequiredMixin(AccessMixin):
    """Ограничивает доступ только для завучей и суперпользователей."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_student:
            return redirect('cards:student_dashboard')
        if not request.user.is_head_teacher and not request.user.is_superuser:
            return redirect('cards:teacher_dashboard')
        return super().dispatch(request, *args, **kwargs)
