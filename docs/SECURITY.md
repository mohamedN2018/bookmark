# SECURITY

## ما أُصلح في المرحلة 1

| # | المشكلة (من PROJECT-AUDIT §7) | الإصلاح | الاختبار |
|---|---|---|---|
| S1 | `DEBUG=True` ثابت | من البيئة، الافتراضي `False` | `check --deploy` |
| S2 | تصعيد صلاحيات عبر toggle staff | منح/سحب staff للمدير العام فقط؛ لا تعديل للحساب الذاتي؛ حسابات superuser لا يعدّلها إلا superuser | `test_security.py::TestUserManagement` |
| S3 | Open redirect بعد الدخول | `url_has_allowed_host_and_scheme` | `TestLogin::test_open_redirect_is_blocked` |
| S4 | تغيير كلمة المرور بلا تحقق | `ProfileForm`: كلمة المرور الحالية + validators + `update_session_auth_hash`؛ البريد فريد | `TestProfile` |
| S7 | `ALLOWED_HOSTS=*`، CSRF origins بلا scheme | من البيئة مع اشتقاق صحيح من `MAIN_DOMAIN` | — |
| S8 | cookies غير secure | `Secure` + `HttpOnly` عند `DEBUG=False`؛ HSTS قابل للتفعيل | `check --deploy` |
| S9 | Logout عبر GET | POST فقط + نماذج CSRF في القوالب | `test_logout_requires_post` |
| S10 | رفع ملفات بلا تحقق | فحص magic bytes + حد للحجم (PDF/صور؛ SVG مرفوض) | `core/tests` |
| S11 | تسريب `str(e)` | أُزيل | — |
| S12 | `\|safe` داخل `<script>` | `json_script` | — |
| S14* | DOM XSS: نص البحث في `innerHTML` (بحث وهمي في الهيدر وفي صفحة التصنيف) والإشعارات | `textContent` | — |
| S15 | migrate أثناء build، `.env` و DB داخل الصورة | `.dockerignore`، migrate عند التشغيل، التطبيق يعمل كمستخدم غير root (`setpriv`) | — |
| — | كلمة مرور قاعدة البيانات | مولّدة عشوائيًا، ليست في المستودع، وقاعدة البيانات غير منشورة على أي منفذ | — |
| — | تخمين كلمات المرور | حد 10 محاولات فاشلة لكل اسم مستخدم خلال 15 دقيقة (Redis cache) | `test_login_is_rate_limited_per_username` |
| — | ملفات الكتب قابلة للوصول عبر `/media/` | محجوبة في `serve_public_media` | `test_book_pdfs_are_not_served_in_production` |
| — | ملفات مرفوعة تُنفّذ كـ HTML | `Content-Security-Policy: default-src 'none'` على `/media/` | — |

## متبقٍ (المرحلة 12)

- CSP كاملة (تتطلب إزالة Tailwind CDN والسكربتات inline، المرحلة 3).
- SSRF validator مركزي لكل URL يُجلب من الخادم (يُبنى مع Source Registry، المرحلة 5).
- rate limiting على مستوى التطبيق لـ API البحث.
- مراجعة `db.sqlite3` في تاريخ git (يحتوي password hashes لحسابين). يُنصح بتغيير كلمتي مرورهما.
