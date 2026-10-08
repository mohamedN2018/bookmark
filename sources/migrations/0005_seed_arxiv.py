from django.db import migrations


def seed(apps, schema_editor):
    Source = apps.get_model("sources", "Source")
    Source.objects.get_or_create(
        slug="arxiv",
        defaults={
            "name": "arXiv",
            "provider_key": "arxiv",
            "source_type": "REPOSITORY",
            "owner": "Cornell University",
            "domain": "arxiv.org",
            "homepage_url": "https://arxiv.org/",
            "terms_url": "https://info.arxiv.org/help/api/tou.html",
            "has_api": True,
            "supports_search": True,
            "supports_metadata": True,
            "allows_rehosting": True,
            "metadata_license": "CC0",
            "legal_access_policy": (
                "مستودع أبحاث ونسخ أولية. لكل بحث رخصة في بياناته الوصفية. نستضيف ملف PDF فقط للأبحاث "
                "برخص Creative Commons (مع النسبة للمؤلفين والرخصة)، ونربط بباقي الأبحاث على arXiv لأن "
                "رخصة arXiv الافتراضية لا تسمح بإعادة الاستضافة. الجلب بمعدل طلب كل 3 ثوانٍ."
            ),
            "rate_limit_per_minute": 20,
            "priority": 75,
            "reliability": 85,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("sources", "0004_seed_open_sources")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
