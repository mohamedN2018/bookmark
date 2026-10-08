from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from core import views as core_views

admin.site.site_header = settings.SITE_NAME
admin.site.site_title = settings.SITE_NAME

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", core_views.health, name="health"),
    path("privacy/", core_views.privacy, name="privacy"),
    path("", include("books.urls")),
]

if settings.DEBUG:
    # في الإنتاج: nginx يخدم /media/ ويحجب /media/books/pdfs/
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", core_views.serve_public_media),
    ]
