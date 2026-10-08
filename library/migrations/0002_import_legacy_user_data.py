from django.db import migrations

from library.legacy import import_legacy_user_data


def forwards(apps, schema_editor):
    import_legacy_user_data(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0001_initial"),
        ("catalog", "0003_import_legacy_books"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
