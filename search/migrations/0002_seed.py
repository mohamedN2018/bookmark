from django.db import migrations

SYNONYMS = [
    "الذكاء الاصطناعي\nartificial intelligence\nAI",
    "تعلم الآلة\nالتعلم الآلي\nmachine learning\nML",
    "التعلم العميق\ndeep learning",
    "الشبكات العصبية\nneural networks\nneural network",
    "معالجة اللغات الطبيعية\nnatural language processing\nNLP",
    "الرؤية الحاسوبية\ncomputer vision",
    "الأمن السيبراني\nأمن المعلومات\ncybersecurity\ncyber security\ninformation security",
    "التشفير\ncryptography",
    "البرمجة\nprogramming",
    "هندسة البرمجيات\nsoftware engineering",
    "قواعد البيانات\ndatabases\ndatabase",
    "شبكات الحاسب\ncomputer networks\nnetworking",
    "الحوسبة السحابية\ncloud computing",
    "علوم البيانات\ndata science",
    "البيانات الضخمة\nbig data",
    "الخوارزميات\nalgorithms\nalgorithm",
    "أنظمة التشغيل\noperating systems",
    "الروبوتات\nrobotics",
    "الرياضيات\nmathematics\nmath",
    "الإحصاء\nstatistics",
    "الفيزياء\nphysics",
    "ميكانيكا الكم\nquantum mechanics",
    "الكيمياء\nchemistry",
    "علم الأحياء\nالأحياء\nbiology",
    "علم الوراثة\ngenetics",
    "الطاقة الشمسية\nsolar energy",
    "طاقة الرياح\nwind energy",
    "الطاقة المتجددة\nrenewable energy",
    "الهندسة الكهربائية\nelectrical engineering",
    "الإلكترونيات\nelectronics",
    "الفلك\nعلم الفلك\nastronomy",
    "المناخ\nclimate",
    "البيئة\nenvironment",
    "الزراعة\nagriculture",
    "الاقتصاد\neconomics",
    "بايثون\npython",
]


def seed(apps, schema_editor):
    Synonym = apps.get_model("search", "Synonym")
    SearchSettings = apps.get_model("search", "SearchSettings")
    SearchSettings.objects.get_or_create(pk=1)
    if not Synonym.objects.exists():
        Synonym.objects.bulk_create([Synonym(terms=terms) for terms in SYNONYMS])


class Migration(migrations.Migration):
    dependencies = [("search", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
