import secrets

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm

from core.utils import parse_grade_class
from .models import Corpus, Subject, User


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
            attrs={'class': 'form-control', 'placeholder': 'Например: 9А или 6ББ'}
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
                'Укажите класс в формате цифры и одной или двух букв (например, 9А или 6ББ).'
            ) from exc

    def clean(self) -> dict:
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get('password')
        pwd2 = cleaned_data.get('confirm_password')
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError('Введенные пароли не совпадают.')
        return cleaned_data

    def clean_first_name(self) -> str:
        val = self.cleaned_data['first_name'].strip()
        if '<' in val or '>' in val:
            raise forms.ValidationError('Имя не должно содержать символы < или >.')
        return val

    def clean_last_name(self) -> str:
        val = self.cleaned_data['last_name'].strip()
        if '<' in val or '>' in val:
            raise forms.ValidationError('Фамилия не должна содержать символы < или >.')
        return val



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
    email = forms.EmailField(
        label='Электронная почта (для уведомлений о заявках)',
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: petrov@yandex.ru'}
        ),
    )
    corpuses = forms.ModelMultipleChoiceField(
        label='Ваши учебные корпуса (можно выбрать несколько)',
        queryset=Corpus.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=True,
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

    def clean_first_name(self) -> str:
        val = self.cleaned_data['first_name'].strip()
        if '<' in val or '>' in val:
            raise forms.ValidationError('Имя не должно содержать символы < или >.')
        return val

    def clean_last_name(self) -> str:
        val = self.cleaned_data['last_name'].strip()
        if '<' in val or '>' in val:
            raise forms.ValidationError('Фамилия не должна содержать символы < или >.')
        return val



class UserProfileForm(forms.Form):
    """Универсальная форма редактирования профиля для учеников, учителей и завучей."""

    last_name = forms.CharField(
        label='Фамилия',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        label='Имя (и Отчество для сотрудников)',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='Электронная почта (для уведомлений о заявках)',
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: teacher@yandex.ru'}
        ),
    )
    class_str = forms.CharField(
        label='Класс',
        max_length=10,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Например: 9А или 6ББ'}
        ),
    )
    corpuses = forms.ModelMultipleChoiceField(
        label='Учебные корпуса (можно выбрать несколько)',
        queryset=Corpus.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
    subjects = forms.ModelMultipleChoiceField(
        label='Преподаваемые предметы',
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
    new_password = forms.CharField(
        label='Новый пароль (оставьте пустым, если не меняете)',
        min_length=6,
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Минимум 6 символов'}
        ),
    )
    confirm_password = forms.CharField(
        label='Повторите новый пароль',
        min_length=6,
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}
        ),
    )

    def __init__(self, *args, user: User, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if not self.is_bound:
            self.fields['last_name'].initial = user.last_name
            self.fields['first_name'].initial = user.first_name
            self.fields['email'].initial = user.email
            if user.is_student and user.grade_num:
                self.fields['class_str'].initial = f'{user.grade_num}{user.grade_letter}'
            if not user.is_student and not user.is_head_teacher and not user.is_superuser:
                self.fields['corpuses'].initial = user.corpuses.all()
                self.fields['subjects'].initial = user.subjects.all()

        # Убираем ненужные поля в зависимости от роли пользователя
        if user.is_student:
            self.fields['class_str'].required = True
            del self.fields['email']
            del self.fields['corpuses']
            del self.fields['subjects']
        elif user.is_head_teacher or user.is_superuser:
            del self.fields['class_str']
            del self.fields['corpuses']
            del self.fields['subjects']
        else:
            del self.fields['class_str']
            self.fields['corpuses'].required = True
            self.fields['subjects'].required = True

    def clean_class_str(self):
        if 'class_str' not in self.fields:
            return None
        value = self.cleaned_data.get('class_str', '')
        try:
            return parse_grade_class(value)
        except ValueError as exc:
            raise forms.ValidationError(
                'Укажите класс в формате цифры и одной или двух букв (например, 9А или 6ББ).'
            ) from exc

    def clean(self) -> dict:
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get('new_password')
        pwd2 = cleaned_data.get('confirm_password')
        if pwd1 or pwd2:
            if pwd1 != pwd2:
                self.add_error('confirm_password', 'Введенные пароли не совпадают.')
        return cleaned_data

    def clean_first_name(self) -> str:
        val = self.cleaned_data['first_name'].strip()
        if '<' in val or '>' in val:
            raise forms.ValidationError('Имя не должно содержать символы < или >.')
        return val

    def clean_last_name(self) -> str:
        val = self.cleaned_data['last_name'].strip()
        if '<' in val or '>' in val:
            raise forms.ValidationError('Фамилия не должна содержать символы < или >.')
        return val
