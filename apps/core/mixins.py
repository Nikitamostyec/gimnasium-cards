from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class StudentRequiredMixin(AccessMixin):
    """Пускает строго активных авторизованных учеников. Всем остальным — 403."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_active or not getattr(request.user, 'is_student', False):
            raise PermissionDenied('Доступ разрешён только ученикам гимназии.')
        return super().dispatch(request, *args, **kwargs)


class TeacherRequiredMixin(AccessMixin):
    """Пускает строго активных учителей-предметников. Ученикам и завучам — 403."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_active:
            raise PermissionDenied('Учётная запись деактивирована.')
        is_student = getattr(request.user, 'is_student', False)
        is_head = getattr(request.user, 'is_head_teacher', False) or request.user.is_superuser
        if is_student or is_head:
            raise PermissionDenied('Этот раздел доступен только учителям-предметникам.')
        return super().dispatch(request, *args, **kwargs)


class HeadTeacherRequiredMixin(AccessMixin):
    """Пускает строго активных завучей и суперпользователей. Остальным — 403."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_active or not (
            getattr(request.user, 'is_head_teacher', False) or request.user.is_superuser
        ):
            raise PermissionDenied('Доступ разрешён только администрации гимназии.')
        return super().dispatch(request, *args, **kwargs)
