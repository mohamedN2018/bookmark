from django.core.management.base import BaseCommand

from catalog.indexing import index_all, index_works
from catalog.models import Work


class Command(BaseCommand):
    help = "يعيد بناء فهرس البحث. مع --missing: يفهرس فقط الأعمال غير المفهرسة (سريع عند كل تشغيل)."

    def add_arguments(self, parser):
        parser.add_argument("--missing", action="store_true")

    def handle(self, *args, **options):
        if options["missing"]:
            ids = list(Work.objects.filter(search_document="").values_list("id", flat=True))
            for start in range(0, len(ids), 500):
                index_works(ids[start : start + 500])
            self.stdout.write(f"[index] فُهرس {len(ids)} عمل غير مفهرس.")
            return
        count = index_all(log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"[index] تمت فهرسة {count} عمل."))
