from django.contrib import admin, messages
from simple_history.admin import SimpleHistoryAdmin

from .models import CardAssignment, Privilege, PrivilegeRequest, Student, Trimester


@admin.register(Trimester)
class TrimesterAdmin(admin.ModelAdmin):
    """Управление учебными триместрами в панели администратора."""

    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.cards.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Управление справочником учеников с безопасным сбросом доступа."""

    list_display = (
        'full_name',
        'grade_num',
        'grade_letter',
        'normalized_class',
        'activation_code',
        'has_user_account',
    )
    list_filter = ('grade_num', 'grade_letter')
    search_fields = ('full_name', 'normalized_name', 'activation_code')
    readonly_fields = (
        'normalized_name',
        'normalized_class',
        'password',
        'activation_code',
        'failed_attempts',
        'locked_until',
    )
    actions = ['reset_student_access']

    @admin.display(boolean=True, description='Привязан аккаунт')
    def has_user_account(self, obj: Student) -> bool:
        return obj.user_id is not None

    @admin.action(description='Сбросить привязку и выдать новый код карты')
    def reset_student_access(self, request, queryset):
        """Отвязывает аккаунт и генерирует новый одноразовый код активации карты."""
        count = 0
        for student in queryset:
            student.user = None
            student.save(update_fields=['user'])
            student.reset_access()
            count += 1
        self.message_user(
            request,
            f'Доступ сброшен для {count} учеников. Сгенерированы новые коды активации.',
            messages.SUCCESS,
        )


@admin.register(CardAssignment)
class CardAssignmentAdmin(SimpleHistoryAdmin):
    """Управление картами учеников с защитой счётчиков от ручной накрутки."""

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
    readonly_fields = (
        'limit',
        'used',
        'grade_removal_credits',
        'grade_removal_used_count',
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def get_readonly_fields(self, request, obj=None):
        """Запрещает изменение типа карты, ученика и триместра после создания."""
        if obj:
            return self.readonly_fields + ('card_type', 'student', 'trimester')
        return self.readonly_fields


@admin.register(Privilege)
class PrivilegeAdmin(admin.ModelAdmin):
    """Управление справочником привилегий (удаление системных кодов запрещено)."""

    list_display = ('code', 'name', 'requires_subject', 'requires_date')
    readonly_fields = ('code',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PrivilegeRequest)
class PrivilegeRequestAdmin(SimpleHistoryAdmin):
    """Просмотр заявок учеников (создание и ручная правка статусов в обход сервиса запрещены)."""

    list_display = (
        'id',
        'card',
        'privilege',
        'corpus',
        'subject',
        'teacher',
        'target_date',
        'status',
        'created_at',
    )
    list_filter = ('status', 'privilege', 'corpus', 'card__trimester')
    search_fields = ('card__student__full_name', 'teacher__last_name')
    readonly_fields = (
        'card',
        'privilege',
        'corpus',
        'subject',
        'teacher',
        'target_date',
        'grade_to_remove',
        'status',
        'rejection_reason',
        'spent_from_reserve',
        'processed_by',
        'created_at',
        'updated_at',
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def has_add_permission(self, request):
        return False
