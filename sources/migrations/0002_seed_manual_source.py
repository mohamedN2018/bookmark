from django.db import migrations


def create_manual_source(apps, schema_editor):
    Source = apps.get_model("sources", "Source")
    Source.objects.get_or_create(
        slug="manual",
        defaults={
            "name": "إدخال يدوي",
            "source_type": "MANUAL",
            "legal_access_policy": (
                "سجلات أُدخلت يدويًا من لوحة الإدارة. حالة الحقوق لكل سجل تُحدد بشكل منفصل "
                "ولا تُفترض. السجلات المنقولة من النسخة الأولى للموقع حالتها UNKNOWN حتى يُتحقق منها."
            ),
            "allows_rehosting": False,
            "priority": 10,
            "reliability": 40,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("sources", "0001_initial")]

    operations = [migrations.RunPython(create_manual_source, migrations.RunPython.noop)]
