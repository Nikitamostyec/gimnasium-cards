from dataclasses import asdict

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import FormView

from cards.models import Trimester
from core.mixins import HeadTeacherRequiredMixin
from .exporters import generate_trimester_report_xlsx
from .forms import StudentImportForm, TrimesterCreateForm
from .importers import commit_imported_students, parse_students_file


class StudentImportView(HeadTeacherRequiredMixin, FormView):
    """Обрабатывает загрузку и предпросмотр списка учеников из Excel или Word."""

    template_name = 'head_teacher/import_preview.html'
    form_class = StudentImportForm

    def form_valid(self, form):
        """Парсит загруженный файл и сохраняет результат в сессии для подтверждения."""
        uploaded_file = form.cleaned_data['file']
        trimester = form.cleaned_data['trimester']

        valid_rows, errors = parse_students_file(
            filename=uploaded_file.name,
            file_bytes=uploaded_file.read(),
        )

        self.request.session['import_payload'] = {
            'trimester_id': trimester.id,
            'rows': [asdict(row) for row in valid_rows],
        }

        return render(
            self.request,
            self.template_name,
            {
                'form': form,
                'trimester': trimester,
                'valid_rows': valid_rows,
                'errors': errors,
                'preview_mode': True,
            },
        )


class StudentImportConfirmView(HeadTeacherRequiredMixin, View):
    """Подтверждает и записывает проверенные данные импорта в базу данных."""

    def post(self, request, *args, **kwargs):
        """Извлекает распарсенные строки из сессии и создает карты ученикам."""
        payload = request.session.pop('import_payload', None)
        if not payload or not payload.get('rows'):
            messages.error(request, 'Нет данных для импорта. Загрузите файл заново.')
            return redirect('reports:import_students')

        trimester = get_object_or_404(Trimester, id=payload['trimester_id'])
        count = commit_imported_students(
            trimester=trimester,
            parsed_rows=payload['rows'],
        )
        messages.success(
            request,
            f'Успешно обработано записей: {count} (триместр: {trimester.name}).',
        )
        return redirect('cards:head_dashboard')


class ExportTrimesterReportView(HeadTeacherRequiredMixin, View):
    """Формирует и отдает на скачивание Excel-отчет за выбранный триместр."""

    def get(self, request, *args, **kwargs):
        """Генерирует файл .xlsx по активному или указанному в параметре триместру."""
        trimester_id = request.GET.get('trimester_id')
        if trimester_id:
            trimester = get_object_or_404(Trimester, id=trimester_id)
        else:
            trimester = Trimester.objects.filter(is_active=True).first()

        if not trimester:
            messages.error(request, 'Не найден активный триместр для выгрузки отчета.')
            return redirect('cards:head_dashboard')

        xlsx_bytes = generate_trimester_report_xlsx(trimester)
        response = HttpResponse(
            xlsx_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        filename = f'report_trimester_{trimester.id}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class TrimesterManageView(HeadTeacherRequiredMixin, FormView):
    """Позволяет завучу создавать новые триместры и переключать активный."""

    template_name = 'head_teacher/trimesters.html'
    form_class = TrimesterCreateForm

    def get_context_data(self, **kwargs):
        """Передает список всех триместров в шаблон."""
        context = super().get_context_data(**kwargs)
        context['trimesters'] = Trimester.objects.all()
        return context

    def form_valid(self, form):
        """Сохраняет новый триместр."""
        trimester = form.save()
        messages.success(self.request, f'Триместр «{trimester.name}» создан.')
        return redirect('reports:manage_trimesters')


class TrimesterActivateView(HeadTeacherRequiredMixin, View):
    """Переключает активный триместр."""

    def post(self, request, pk: int, *args, **kwargs):
        """Делает выбранный триместр активным, автоматически архивируя остальные."""
        trimester = get_object_or_404(Trimester, id=pk)
        trimester.is_active = True
        trimester.save()
        messages.success(request, f'Активный триместр изменен на «{trimester.name}».')
        return redirect('reports:manage_trimesters')
