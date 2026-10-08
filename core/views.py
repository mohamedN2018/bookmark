from django.conf import settings
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.static import serve


@never_cache
def health(request):
    """فحص صحة بسيط للـ load balancer / docker healthcheck."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok}, status=status)


def serve_public_media(request, path):
    """خدمة media العامة (أغلفة، صور مؤلفين) مع حجب ملفات الكتب المحمية."""
    if path.startswith(settings.PROTECTED_MEDIA_PREFIXES):
        raise Http404
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response["Cache-Control"] = "public, max-age=604800"
    # لا يُنفّذ أي ملف مرفوع كصفحة HTML/JS
    response["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"
    return response


def privacy(request):
    return render(request, "pages/privacy.html")
