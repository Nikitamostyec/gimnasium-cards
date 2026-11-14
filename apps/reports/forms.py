from django import forms

from cards.models import Trimester


class StudentImportForm(forms.Form):
    """Форма загрузки файла Excel или Word со списком обладателей карт."""

    trimester = forms.ModelChoiceField(
        label='Целевой триместр',
        queryset=Trimester.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    file = forms.FileField(
        label='Файл со списком (.xlsx или .docx)',
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
                'accept': '.xlsx,.docx',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        """По умолчанию выбирает текущий активный триместр."""
        super().__init__(*args, **kwargs)
        active = Trimester.objects.filter(is_active=True).first()
        if active:
            self.fields['trimester'].initial = active


class TrimesterCreateForm(forms.ModelForm):
    """Форма создания нового учебного триместра."""

    class Meta:
        model = Trimester
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Например: 2 триместр 2026/2027',
                }
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
