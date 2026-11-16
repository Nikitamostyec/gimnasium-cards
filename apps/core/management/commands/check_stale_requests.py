from django.core.management.base import BaseCommand
from cards.services import RequestService


class Command(BaseCommand):
    help = 'Проверяет зависшие и просроченные заявки, возвращает баллы и отправляет напоминания.'

    def handle(self, *args, **options):
        stats = RequestService.process_stale_requests()
        self.stdout.write(
            self.style.SUCCESS(
                f"Проверка завершена: авто-отменено {stats['expired']}, отправлено напоминаний {stats['reminded']}."
            )
        )
