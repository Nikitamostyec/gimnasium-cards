import secrets

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm

from core.utils import parse_grade_class
from .models import Subject, User


class StaffLoginForm(AuthenticationForm):
    """Форма аутентификации учителей и завучей со стилями Bootstrap 5."""

    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Введите логин',
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


class StudentRegisterForm(forms.Form):
    """Форма свободной регистрации любого ученика гимназии."""

    username = forms.CharField(
        label='Придумайте логин (на английском)',
        min_length=3,
        max_length=50,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Например: ivan_9a',
                'autocomplete': 'off',
            }
        ),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=100,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: Иванов'}
        ),
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=100,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: Иван'}
        ),
    )
    class_str = forms.CharField(
        label='Класс',
        max_length=10,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: 9А'}
        ),
    )
    password = forms.CharField(
        label='Придумайте пароль',
        min_length=6,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Минимум 6 символов'}
        ),
    )
    confirm_password = forms.CharField(
        label='Повторите пароль',
        min_length=6,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}
        ),
    )

    def clean_username(self) -> str:
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Этот логин уже занят. Придумайте другой.')
        return username

    def clean_class_str(self) -> tuple[int, str]:
        value = self.cleaned_data['class_str']
        try:
            return parse_grade_class(value)
        except ValueError as exc:
            raise forms.ValidationError(
                'Укажите класс в формате цифры и буквы (например, 9А).'
            ) from exc

    def clean(self) -> dict:
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get('password')
        pwd2 = cleaned_data.get('confirm_password')
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError('Введенные пароли не совпадают.')
        return cleaned_data


class TeacherRegisterForm(forms.Form):
    """Форма самостоятельной регистрации учителя-предметника с защитой инвайт-кодом."""

    invite_code = forms.CharField(
        label='Секретный код школы (выдаётся завучем)',
        max_length=50,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Введите код для учителей',
                'autocomplete': 'off',
            }
        ),
    )
    username = forms.CharField(
        label='Придумайте логин',
        min_length=3,
        max_length=50,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: petrov_math'}
        ),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=100,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: Петров'}
        ),
    )
    first_name = forms.CharField(
        label='Имя и Отчество',
        max_length=150,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: Сергей Александрович'}
        ),
    )
    subjects = forms.ModelMultipleChoiceField(
        label='Ваши предметы (можно выбрать несколько)',
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=True,
    )
    password = forms.CharField(
        label='Придумайте пароль',
        min_length=6,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Минимум 6 символов'}
        ),
    )
    confirm_password = forms.CharField(
        label='Повторите пароль',
        min_length=6,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}
        ),
    )

    def clean_invite_code(self) -> str:
        code = self.cleaned_data['invite_code'].strip()
        expected = getattr(settings, 'TEACHER_INVITE_CODE', 'GIM16-TEACHER')
        if not secrets.compare_digest(code, expected):
            raise forms.ValidationError('Неверный секретный код школы. Уточните код у завуча.')
        return code

    def clean_username(self) -> str:
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Этот логин уже занят.')
        return username

    def clean(self) -> dict:
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get('password')
        pwd2 = cleaned_data.get('confirm_password')
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError('Введенные пароли не совпадают.')
        return cleaned_data
