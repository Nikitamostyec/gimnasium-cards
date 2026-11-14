"""Маршрутизация кабинетов ученика, учителя-предметника и завуча."""

from django.urls import path

from .views import (
    HeadTeacherDashboardView,
    StaffChangeRequestStatusView,
    StudentActivateCardView,
    StudentCreateRequestView,
    StudentDashboardView,
    StudentLoginView,
    StudentLogoutView,
    StudentRequestFormPartialView,
    TeacherDashboardView,
)

app_name = 'cards'

urlpatterns = [
    path('', StudentLoginView.as_view(), name='student_login'),
    path('logout/', StudentLogoutView.as_view(), name='student_logout'),
    path('dashboard/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('activate-card/', StudentActivateCardView.as_view(), name='activate_card'),
    path('request/create/', StudentCreateRequestView.as_view(), name='create_request'),
    path(
        'request/form/<str:code>/',
        StudentRequestFormPartialView.as_view(),
        name='request_form_partial',
    ),
    path('teacher/', TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('head/', HeadTeacherDashboardView.as_view(), name='head_dashboard'),
    path(
        'request/<int:pk>/<str:action>/',
        StaffChangeRequestStatusView.as_view(),
        name='change_request_status',
    ),
]
