from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.legacy import import_legacy_books
from library.legacy import import_legacy_user_data


class Command(BaseCommand):
    help = "ينقل كتب وبيانات مستخدمي النموذج القديم (books) إلى الفهرس ومكتبة المستخدم. آمن للتكرار."

    def handle(self, *args, **options):
        with transaction.atomic():
            books = import_legacy_books(apps)
            users = import_legacy_user_data(apps)
        self.stdout.write(
            f"[legacy-books] كتب: {books}، محفوظات: {users['saved']}، "
            f"تقييمات: {users['ratings']}، سجل: {users['history']}"
        )
