"""Маршрутизация импорта списков, экспорта отчетов и управления триместрами."""

from django.urls import path

from .views import (
    DownloadImportTemplateView,
    ExportTrimesterReportView,
    StudentImportConfirmView,
    StudentImportView,
    TrimesterActivateView,
    TrimesterManageView,
)

app_name = 'reports'

urlpatterns = [
    path('import/', StudentImportView.as_view(), name='import_students'),
    path(
        'import/confirm/',
        StudentImportConfirmView.as_view(),
        name='import_students_confirm',
    ),
    path('export/', ExportTrimesterReportView.as_view(), name='export_report'),
    path('trimesters/', TrimesterManageView.as_view(), name='manage_trimesters'),
    path(
        'trimesters/<int:pk>/activate/',
        TrimesterActivateView.as_view(),
        name='activate_trimester',
    ),
    path(
        'import/template/',
        DownloadImportTemplateView.as_view(),
        name='download_import_template',
    )
]
