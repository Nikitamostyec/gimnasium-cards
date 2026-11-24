"""Корневая конфигурация URL-маршрутов проекта."""

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import include, path
from django.views.generic import TemplateView


def admin_access_guard(view_func):
    """Запрещает доступ к панели администратора всем, кроме завучей и суперпользователей."""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            raise PermissionDenied('Доступ к панели управления запрещён.')
        if not (getattr(request.user, 'is_head_teacher', False) or request.user.is_superuser):
            raise PermissionDenied('У вас нет прав администратора гимназии.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Оборачиваем стандартный вход в админку Django нашей проверкой прав (403 вместо чужой формы входа)
admin.site.login = admin_access_guard(admin.site.login)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('staff/', include('users.urls')),
    path('reports/', include('reports.urls')),
    path('', include('cards.urls')),
    path(
        'about/',
        TemplateView.as_view(
            template_name='about.html',
            http_method_names=['get', 'head', 'options'],
        ),
        name='about',
    ),
    path(
        'guide/',
        TemplateView.as_view(
            template_name='guide.html',
            http_method_names=['get', 'head', 'options'],
        ),
        name='guide',
    ),
    path('grades/', include('grades.urls')),
]


def custom_403_view(request, exception=None):
    return render(request, '403.html', status=403)


def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)


def custom_500_view(request):
    return render(request, '500.html', status=500)


handler403 = 'config.urls.custom_403_view'
handler404 = 'config.urls.custom_404_view'
handler500 = 'config.urls.custom_500_view'
