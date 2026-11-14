"""Корневая конфигурация URL-маршрутов проекта."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('staff/', include('users.urls')),
    path('reports/', include('reports.urls')),
    path('', include('cards.urls')),
]
