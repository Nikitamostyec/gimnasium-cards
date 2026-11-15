from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Corpus, Subject, User


@admin.register(Corpus)
class CorpusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'last_name',
        'first_name',
        'get_role_display',
        'get_corpuses_list',
        'is_active',
    )
    list_filter = ('is_student', 'is_head_teacher', 'is_active', 'corpuses', 'subjects')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    filter_horizontal = ('corpuses', 'subjects', 'groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'email')}),
        (
            'Роль и привязка в гимназии',
            {
                'fields': (
                    'is_student',
                    'is_head_teacher',
                    'corpuses',
                    'subjects',
                    'grade_num',
                    'grade_letter',
                )
            },
        ),
        (
            'Защита от перебора кода',
            {'fields': ('failed_code_attempts', 'code_locked_until')},
        ),
        (
            'Права доступа (системные)',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )

    @admin.display(description='Роль')
    def get_role_display(self, obj: User) -> str:
        if obj.is_superuser:
            return 'Администратор (Superuser)'
        if obj.is_head_teacher:
            return 'Завуч'
        if obj.is_student:
            return f'Ученик ({obj.grade_num or ""}{obj.grade_letter})'
        return 'Учитель'

    @admin.display(description='Корпуса')
    def get_corpuses_list(self, obj: User) -> str:
        return ', '.join(c.name for c in obj.corpuses.all()) or '—'

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.extend(['is_superuser', 'is_staff', 'user_permissions', 'groups'])
        return readonly

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.pk == request.user.pk:
            return False
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)