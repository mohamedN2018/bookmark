from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("library/", views.my_library, name="my_library"),
    path("library/save/<int:work_id>/", views.toggle_save, name="toggle_save"),
    path("library/rate/<int:work_id>/", views.rate, name="rate_work"),
    # روابط النسخة الأولى
    path("dashboard/", RedirectView.as_view(pattern_name="my_library", permanent=True)),
    path("dashboard/books/", RedirectView.as_view(url="/admin/catalog/work/", permanent=False)),
    path("dashboard/users/", RedirectView.as_view(url="/admin/auth/user/", permanent=False)),
    path("dashboard/settings/", RedirectView.as_view(url="/admin/", permanent=False)),
]
