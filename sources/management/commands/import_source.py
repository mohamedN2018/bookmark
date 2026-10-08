from django.core.management.base import BaseCommand, CommandError

from sources.pipeline import ImportPipeline
from sources.providers import PROVIDERS, get_provider


class Command(BaseCommand):
    help = "استيراد كتب من مصدر مفتوح (oapen | gutenberg). آمن للتكرار."

    def add_arguments(self, parser):
        parser.add_argument("provider", choices=sorted(PROVIDERS))
        parser.add_argument("--limit", type=int, default=None, help="أقصى عدد سجلات جديدة")
        parser.add_argument("--download", action="store_true", help="تنزيل واستضافة الملفات المرخصة")
        parser.add_argument("--all-subjects", action="store_true", help="عدم الاقتصار على الموضوعات العلمية")
        parser.add_argument("--language", action="append", default=[], help="فلترة باللغة (ISO-1)، قابلة للتكرار")
        parser.add_argument("--resume", default="", help="resumption token لاستكمال عملية سابقة (OAPEN)")
        parser.add_argument("--max-total-mb", type=int, default=None, help="حد إجمالي حجم التنزيل لهذه العملية")
        parser.add_argument(
            "--set", dest="oai_set", default="", help="مجموعة OAI (arXiv: cs, math, physics, q-bio, stat, eess, econ)"
        )
        parser.add_argument("--days", type=int, default=None, help="arXiv: السجلات المحدثة خلال آخر N يومًا")

    def handle(self, *args, **options):
        provider = get_provider(options["provider"])
        pipeline = ImportPipeline(
            provider,
            download_files=options["download"],
            science_only=not options["all_subjects"],
            languages=options["language"],
            limit=options["limit"],
            max_total_bytes=options["max_total_mb"] * 1024 * 1024 if options["max_total_mb"] else None,
            log=self.stdout.write,
        )
        params = {"resume_token": options["resume"]} if options["resume"] else {}
        if options["oai_set"]:
            params["oai_set"] = options["oai_set"]
        if options["days"]:
            params["days"] = options["days"]
        try:
            job = pipeline.run(**params)
        except Exception as exc:
            raise CommandError(f"فشل الاستيراد: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"[{provider.key}] انتهى: مقروء {job.seen} · جديد {job.created} · محدّث {job.updated} · "
                f"مكرر {job.duplicates} · تخطي {job.skipped} · ملفات {job.files_downloaded} "
                f"({job.bytes_downloaded // (1024 * 1024)}MB) · أخطاء {job.errors}"
            )
        )
        if job.cursor:
            self.stdout.write(f"للاستكمال: --resume '{job.cursor}'")
