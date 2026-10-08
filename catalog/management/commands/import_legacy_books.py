from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.legacy import import_legacy_books


class Command(BaseCommand):
    help = "ينقل كتب النموذج القديم (books.Book) إلى الفهرس الجديد. آمن للتكرار."

    def handle(self, *args, **options):
        with transaction.atomic():
            count = import_legacy_books(apps)
        self.stdout.write(f"[legacy-books] نُقل {count} كتاب إلى الفهرس.")
