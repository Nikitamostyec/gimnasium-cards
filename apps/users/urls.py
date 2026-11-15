"""Маршрутизация аутентификации и регистрации пользователей гимназии."""

from django.urls import path

from .views import (
    StaffLoginView,
    StaffLogoutView,
    StudentRegisterView,
    TeacherRegisterView,
    UserProfileView,
)

app_name = 'users'

urlpatterns = [
    path('login/', StaffLoginView.as_view(), name='login'),
    path('logout/', StaffLogoutView.as_view(), name='logout'),
    path('register/student/', StudentRegisterView.as_view(), name='student_register'),
    path('register/teacher/', TeacherRegisterView.as_view(), name='teacher_register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]
