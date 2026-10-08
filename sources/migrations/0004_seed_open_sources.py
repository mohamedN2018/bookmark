from django.db import migrations

SOURCES = [
    {
        "slug": "oapen",
        "name": "OAPEN Library",
        "provider_key": "oapen",
        "source_type": "REPOSITORY",
        "owner": "OAPEN Foundation",
        "domain": "library.oapen.org",
        "homepage_url": "https://library.oapen.org/",
        "terms_url": "https://www.oapen.org/about",
        "has_api": True,
        "supports_search": True,
        "supports_metadata": True,
        "allows_rehosting": True,
        "metadata_license": "CC0",
        "legal_access_policy": (
            "مكتبة كتب أكاديمية مفتوحة الوصول ومحكّمة. كل ملف منشور برخصة Creative Commons "
            "مذكورة في بياناته الوصفية (rights/rightsuri). نستضيف الملف فقط إذا كانت رخصته صريحة، "
            "ونعرض الرخصة والمصدر والمؤلفين (شرط النسبة). الرخص NC تمنع الاستخدام التجاري."
        ),
        "rate_limit_per_minute": 30,
        "priority": 80,
        "reliability": 90,
    },
    {
        "slug": "gutenberg",
        "name": "Project Gutenberg",
        "provider_key": "gutenberg",
        "source_type": "LIBRARY",
        "owner": "Project Gutenberg Literary Archive Foundation",
        "domain": "www.gutenberg.org",
        "homepage_url": "https://www.gutenberg.org/",
        "terms_url": "https://www.gutenberg.org/policy/robot_access.html",
        "has_api": False,
        "supports_search": False,
        "supports_metadata": True,
        "allows_rehosting": False,
        "metadata_license": "Public Domain",
        "legal_access_policy": (
            "كتب في الملكية العامة في الولايات المتحدة. نقرأ الفهرس من ملف pg_catalog.csv الرسمي، "
            "ونربط بالقراءة والتحميل من موقع Gutenberg دون جلب آلي للملفات من الموقع الرئيسي "
            "(سياسة الوصول الآلي لديهم). حالة الملكية العامة قد تختلف خارج الولايات المتحدة."
        ),
        "priority": 70,
        "reliability": 85,
    },
]


def seed(apps, schema_editor):
    Source = apps.get_model("sources", "Source")
    for data in SOURCES:
        Source.objects.get_or_create(slug=data["slug"], defaults=data)


class Migration(migrations.Migration):
    dependencies = [("sources", "0003_import_job")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
