from django.contrib import admin, messages
from simple_history.admin import SimpleHistoryAdmin

from .models import CardAssignment, Privilege, PrivilegeRequest, Student, Trimester


@admin.register(Trimester)
class TrimesterAdmin(admin.ModelAdmin):
    """Управление учебными триместрами в панели администратора."""

    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Управление справочником учеников с возможностью сброса пароля."""

    list_display = (
        'full_name',
        'grade_num',
        'grade_letter',
        'normalized_class',
        'has_password',
    )
    list_filter = ('grade_num', 'grade_letter')
    search_fields = ('full_name', 'normalized_name')
    readonly_fields = ('normalized_name', 'normalized_class', 'password')
    actions = ['reset_student_passwords']

    @admin.display(boolean=True, description='Пароль задан')
    def has_password(self, obj: Student) -> bool:
        """Отображает статус активации кабинета ученика в списке."""
        return obj.has_password

    @admin.action(description='Сбросить пароль выбранным ученикам')
    def reset_student_passwords(self, request, queryset):
        """Очищает хэш пароля, позволяя ученику задать новый при следующем входе."""
        updated = queryset.update(password='')
        self.message_user(
            request,
            f'Пароли сброшены для {updated} учеников.',
            messages.SUCCESS,
        )


@admin.register(CardAssignment)
class CardAssignmentAdmin(SimpleHistoryAdmin):
    """Управление картами учеников с фиксацией истории ручных изменений."""

    list_display = (
        'student',
        'trimester',
        'card_type',
        'used',
        'limit',
        'grade_removal_credits',
        'grade_removal_used_count',
    )
    list_filter = ('trimester', 'card_type')
    search_fields = ('student__full_name', 'student__normalized_name')
    readonly_fields = ('limit',)

    def get_readonly_fields(self, request, obj=None):
        """Запрещает изменение типа карты после ее создания."""
        if obj:
            return self.readonly_fields + ('card_type', 'student', 'trimester')
        return self.readonly_fields


@admin.register(Privilege)
class PrivilegeAdmin(admin.ModelAdmin):
    """Управление справочником привилегий."""

    list_display = ('code', 'name', 'requires_subject', 'requires_date')


@admin.register(PrivilegeRequest)
class PrivilegeRequestAdmin(SimpleHistoryAdmin):
    """Управление заявками учеников с фиксацией истории изменений."""

    list_display = (
        'id',
        'card',
        'privilege',
        'subject',
        'target_date',
        'status',
        'created_at',
    )
    list_filter = ('status', 'privilege', 'card__trimester')
    search_fields = ('card__student__full_name',)
