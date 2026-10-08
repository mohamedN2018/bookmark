"""التصنيف العلمي الأساسي (قابل للتعديل والتوسعة من لوحة الإدارة)."""

from django.db import migrations

from core.arabic import normalize_key

# (الاسم العربي، الاسم الإنجليزي، slug، الأبناء)
TAXONOMY = [
    (
        "علوم الحاسب",
        "Computer Science",
        "computer-science",
        [
            ("البرمجة", "Programming", "programming", []),
            ("هندسة البرمجيات", "Software Engineering", "software-engineering", []),
            (
                "الذكاء الاصطناعي",
                "Artificial Intelligence",
                "artificial-intelligence",
                [
                    (
                        "تعلم الآلة",
                        "Machine Learning",
                        "machine-learning",
                        [("التعلم العميق", "Deep Learning", "deep-learning", [])],
                    ),
                    ("معالجة اللغات الطبيعية", "Natural Language Processing", "nlp", []),
                    ("الرؤية الحاسوبية", "Computer Vision", "computer-vision", []),
                    ("الروبوتات", "Robotics", "robotics", []),
                ],
            ),
            ("علوم البيانات", "Data Science", "data-science", []),
            ("قواعد البيانات", "Databases", "databases", []),
            ("أنظمة التشغيل", "Operating Systems", "operating-systems", []),
            ("الشبكات", "Computer Networks", "networks", []),
            (
                "الأمن السيبراني",
                "Cybersecurity",
                "cybersecurity",
                [("التشفير", "Cryptography", "cryptography", [])],
            ),
            ("الأنظمة الموزعة", "Distributed Systems", "distributed-systems", []),
            ("الحوسبة السحابية", "Cloud Computing", "cloud-computing", []),
            ("DevOps", "DevOps", "devops", []),
            ("هندسة موثوقية المواقع", "Site Reliability Engineering", "sre", []),
            ("رسوميات الحاسب", "Computer Graphics", "computer-graphics", []),
        ],
    ),
    (
        "الرياضيات",
        "Mathematics",
        "mathematics",
        [("الإحصاء", "Statistics", "statistics", [])],
    ),
    (
        "الفيزياء",
        "Physics",
        "physics",
        [
            ("الفيزياء النظرية", "Theoretical Physics", "theoretical-physics", []),
            ("الفيزياء التطبيقية", "Applied Physics", "applied-physics", []),
            ("الفيزياء النووية", "Nuclear Physics", "nuclear-physics", []),
        ],
    ),
    (
        "الطاقة",
        "Energy",
        "energy",
        [
            ("الطاقة الشمسية", "Solar Energy", "solar-energy", []),
            ("طاقة الرياح", "Wind Energy", "wind-energy", []),
            ("الشبكات الكهربائية", "Power Grids", "power-grids", []),
            ("تخزين الطاقة", "Energy Storage", "energy-storage", []),
            ("الهيدروجين", "Hydrogen", "hydrogen", []),
            (
                "الطاقة النووية",
                "Nuclear Energy",
                "nuclear-energy",
                [
                    ("المفاعلات النووية", "Nuclear Reactors", "nuclear-reactors", []),
                    ("السلامة النووية", "Nuclear Safety", "nuclear-safety", []),
                ],
            ),
        ],
    ),
    (
        "الهندسة",
        "Engineering",
        "engineering",
        [
            ("الهندسة الكهربائية", "Electrical Engineering", "electrical-engineering", []),
            ("الهندسة الميكانيكية", "Mechanical Engineering", "mechanical-engineering", []),
            ("الإلكترونيات", "Electronics", "electronics", []),
            ("الهندسة المدنية", "Civil Engineering", "civil-engineering", []),
            ("الهندسة الكيميائية", "Chemical Engineering", "chemical-engineering", []),
            ("الهندسة الصناعية", "Industrial Engineering", "industrial-engineering", []),
            ("هندسة الطيران", "Aerospace Engineering", "aerospace-engineering", []),
            ("الميكاترونكس", "Mechatronics", "mechatronics", []),
        ],
    ),
    (
        "العلوم الحيوية والكيمياء",
        "Life Sciences and Chemistry",
        "life-sciences",
        [
            ("الأحياء", "Biology", "biology", []),
            (
                "الكيمياء",
                "Chemistry",
                "chemistry",
                [("الكيمياء العضوية", "Organic Chemistry", "organic-chemistry", [])],
            ),
            ("الكيمياء الحيوية", "Biochemistry", "biochemistry", []),
            ("الطب الحيوي", "Biomedicine", "biomedicine", []),
            ("علم الوراثة", "Genetics", "genetics", []),
        ],
    ),
    (
        "الزراعة",
        "Agriculture",
        "agriculture",
        [
            ("الزراعة الذكية", "Smart Agriculture", "smart-agriculture", []),
            ("التقنيات الزراعية", "Agritech", "agritech", []),
            ("الري", "Irrigation", "irrigation", []),
            ("علوم التربة", "Soil Science", "soil-science", []),
            ("الروبوتات الزراعية", "Agricultural Robotics", "agricultural-robotics", []),
            ("الاستشعار عن بعد", "Remote Sensing", "remote-sensing", []),
        ],
    ),
    (
        "الفضاء وعلوم الأرض",
        "Space and Earth Sciences",
        "space-earth-sciences",
        [
            ("الفضاء", "Space Science", "space-science", []),
            ("الفلك", "Astronomy", "astronomy", []),
            ("علوم الأرض", "Earth Sciences", "earth-sciences", []),
            ("المناخ", "Climate", "climate", []),
            ("البيئة", "Environment", "environment", []),
        ],
    ),
    (
        "الاقتصاد",
        "Economics",
        "economics",
        [
            ("اقتصاد التكنولوجيا", "Economics of Technology", "economics-of-technology", []),
            ("إدارة التكنولوجيا", "Technology Management", "technology-management", []),
        ],
    ),
]


def seed(apps, schema_editor):
    Subject = apps.get_model("catalog", "Subject")

    def create(nodes, parent=None):
        for order, (name, name_en, slug, children) in enumerate(nodes):
            subject, _ = Subject.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "name_en": name_en,
                    "parent": parent,
                    "sort_order": order,
                    # الـ save() المخصص لا يعمل داخل migrations، لذا نحسبها هنا
                    "normalized_name": normalize_key(f"{name} {name_en}"),
                },
            )
            create(children, subject)

    create(TAXONOMY)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
