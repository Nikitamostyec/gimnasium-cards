
from django.shortcuts import render


def calculator(request):
    """Публичный калькулятор оценок для всех посетителей."""
    return render(request, 'grades/calculator.html')
