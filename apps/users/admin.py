from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Subject, User


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Управление справочником учебных предметов в панели администратора."""

    list_display = ('name',)
    search_fields = ('name',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Управление учетными записями учителей и завучей."""

    list_display = (
        'username',
        'first_name',
        'last_name',
        'is_head_teacher',
        'is_staff',
    )
    list_filter = ('is_head_teacher', 'is_staff', 'subjects')
    filter_horizontal = ('subjects', 'groups', 'user_permissions')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Роль в гимназии', {'fields': ('is_head_teacher', 'subjects')}),
    )
