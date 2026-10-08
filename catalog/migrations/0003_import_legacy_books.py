from django.db import migrations

from catalog.legacy import import_legacy_books


def forwards(apps, schema_editor):
    import_legacy_books(apps)


def backwards(apps, schema_editor):
    Work = apps.get_model("catalog", "Work")
    Work.objects.filter(legacy_book__isnull=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_seed_taxonomy"),
        ("sources", "0002_seed_manual_source"),
        ("books", "0004_phase1_safety"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
