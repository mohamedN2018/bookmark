"""فهارس البحث على PostgreSQL فقط: pg_trgm + GIN على search_vector وعلى normalized_title."""

from django.db import migrations

FORWARD = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS catalog_work_search_vector_gin ON catalog_work USING gin (search_vector)",
    "CREATE INDEX IF NOT EXISTS catalog_work_title_trgm ON catalog_work USING gin (normalized_title gin_trgm_ops)",
]
BACKWARD = [
    "DROP INDEX IF EXISTS catalog_work_title_trgm",
    "DROP INDEX IF EXISTS catalog_work_search_vector_gin",
]


def _run(statements):
    def operation(apps, schema_editor):
        if schema_editor.connection.vendor != "postgresql":
            return
        for statement in statements:
            schema_editor.execute(statement)

    return operation


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_work_search_document_work_search_vector")]

    operations = [migrations.RunPython(_run(FORWARD), _run(BACKWARD))]
