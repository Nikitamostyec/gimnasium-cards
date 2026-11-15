from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def student_required(view_func):
    """Пускает только авторизованных учеников. Остальным — 403."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not getattr(request.user, 'is_student', False):
            raise PermissionDenied('Этот раздел доступен только ученикам.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def teacher_required(view_func):
    """Пускает только учителей-предметников (не учеников и не завучей). Остальным — 403."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        is_student = getattr(request.user, 'is_student', False)
        is_head = getattr(request.user, 'is_head_teacher', False) or request.user.is_superuser
        if is_student or is_head:
            raise PermissionDenied('Этот кабинет предназначен только для учителей-предметников.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def head_teacher_required(view_func):
    """Пускает только завучей и суперпользователей. Остальным — 403."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (getattr(request.user, 'is_head_teacher', False) or request.user.is_superuser):
            raise PermissionDenied('Доступ разрешён только администрации гимназии.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_required(view_func):
    """Пускает любого сотрудника школы (учителя или завуча). Ученикам — 403."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if getattr(request.user, 'is_student', False):
            raise PermissionDenied('Ученикам доступ в этот раздел запрещён.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
