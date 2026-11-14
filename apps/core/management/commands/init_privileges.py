from django.core.management.base import BaseCommand
from cards.models import Privilege


class Command(BaseCommand):
    """Management-команда для первичного наполнения и обновления справочника 6 привилегий."""

    help = 'Создает или обновляет базовый каталог из 6 привилегий в базе данных.'

    def handle(self, *args, **options):
        """Выполняет идемпотентную загрузку справочника привилегий."""
        privileges_data = [
            {
                'code': Privilege.Code.SKIP_DAY,
                'name': 'Освобождение от учебных занятий на 1 день',
                'requires_subject': False,
                'requires_date': True,
            },
            {
                'code': Privilege.Code.SKIP_TEST,
                'name': 'Освобождение от написания одной контрольной работы',
                'requires_subject': True,
                'requires_date': False,
            },
            {
                'code': Privilege.Code.SKIP_MIN,
                'name': 'Освобождение от сдачи «образовательного минимума»',
                'requires_subject': True,
                'requires_date': False,
            },
            {
                'code': Privilege.Code.ADD_NINE,
                'name': 'Выставление в журнал одной оценки «9»',
                'requires_subject': True,
                'requires_date': False,
            },
            {
                'code': Privilege.Code.DROP_GRADE,
                'name': 'Право отказаться от текущих оценок (Пакет)',
                'requires_subject': True,
                'requires_date': False,
            },
            {
                'code': Privilege.Code.SKIP_PRACTICE,
                'name': 'Освобождение от летней трудовой практики',
                'requires_subject': False,
                'requires_date': False,
            },
        ]

        for item in privileges_data:
            Privilege.objects.update_or_create(
                code=item['code'],
                defaults={
                    'name': item['name'],
                    'requires_subject': item['requires_subject'],
                    'requires_date': item['requires_date'],
                },
            )
        self.stdout.write(self.style.SUCCESS('Справочник привилегий успешно инициализирован.'))
