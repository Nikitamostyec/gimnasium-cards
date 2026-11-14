from datetime import timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from users.models import Subject
from .models import Privilege


class StudentAccountLoginForm(AuthenticationForm):
    """Форма входа ученика по личному логину и паролю."""

    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Введите ваш логин',
                'autofocus': True,
            }
        ),
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Введите пароль',
            }
        ),
    )


class ActivateCardForm(forms.Form):
    """Форма активации карты привилегий по секретному коду от завуча."""

    activation_code = forms.CharField(
        label='Секретный код карты (выдаётся завучем)',
        max_length=12,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg text-uppercase',
                'placeholder': 'Например: K7M9-P4X2',
                'autocomplete': 'off',
            }
        ),
    )

    def clean_activation_code(self) -> str:
        return self.cleaned_data['activation_code'].strip().upper()


class CreatePrivilegeRequestForm(forms.Form):
    """Форма создания заявки на использование привилегии."""

    privilege_code = forms.ChoiceField(
        choices=Privilege.Code.choices,
        widget=forms.HiddenInput(),
    )
    subject = forms.ModelChoiceField(
        label='Выберите предмет',
        queryset=Subject.objects.all(),
        required=False,
        empty_label='--- Выберите предмет ---',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    target_date = forms.DateField(
        label='Желаемая дата освобождения',
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
            }
        ),
    )
    grade_to_remove = forms.IntegerField(
        label='Какую оценку убрать (от 1 до 10)',
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'placeholder': 'Введите оценку от 1 до 10',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        min_date = timezone.localdate() + timedelta(days=2)
        self.fields['target_date'].widget.attrs['min'] = min_date.isoformat()

    def clean(self) -> dict:
        cleaned_data = super().clean()
        code = cleaned_data.get('privilege_code')
        grade = cleaned_data.get('grade_to_remove')

        if code == Privilege.Code.DROP_GRADE and grade is None:
            self.add_error(
                'grade_to_remove',
                'Укажите конкретную оценку (от 1 до 10), от которой хотите отказаться.',
            )
        return cleaned_data


class RejectRequestForm(forms.Form):
    """Форма отклонения заявки учителем или завучем с обязательной причиной."""

    reason = forms.CharField(
        label='Причина отклонения',
        max_length=500,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Укажите причину отказа...',
            }
        ),
    )

    def clean_reason(self) -> str:
        reason = self.cleaned_data['reason'].strip()
        if not reason:
            raise forms.ValidationError('Причина отклонения не может быть пустой.')
        return reason
