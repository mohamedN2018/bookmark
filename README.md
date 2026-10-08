# المكتبة السرية

> المعرفة التي يصعب الوصول إليها، في مكان واحد.

منصة عربية لاكتشاف وفهرسة المصادر العلمية والتقنية، مع توضيح مصدر كل مادة ونوع الوصول القانوني إليها.

## التشغيل المحلي

```sh
cp .env.example .env   # ثم عدّل القيم
docker compose up -d --build
```

أو بدون Docker (SQLite للتطوير فقط):

```sh
pip install -r requirements-dev.txt
DEBUG=True python manage.py migrate
DEBUG=True python manage.py runserver
```

## الاختبارات

```sh
docker compose -f docker-compose.test.yml run --rm --build tests
```

## التوثيق

- [docs/PROJECT-AUDIT.md](docs/PROJECT-AUDIT.md): فحص المشروع الأصلي وخطة الترحيل
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/SECURITY.md](docs/SECURITY.md)
