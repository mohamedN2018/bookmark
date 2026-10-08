from django.urls import path, register_converter

from core.converters import UnicodeSlugConverter

from . import views

register_converter(UnicodeSlugConverter, "uslug")

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.search, name="search"),
    path("books/<uslug:slug>/", views.work_detail, name="work_detail"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    path("topics/", views.topics, name="topics"),
    path("topics/<uslug:slug>/", views.topic_detail, name="topic_detail"),
    path("authors/", views.people, name="people"),
    path("people/<uslug:slug>/", views.person_detail, name="person_detail"),
    path("access/<int:link_id>/file/", views.hosted_file, name="hosted_file"),
    # روابط النسخة الأولى
    path("categories/", views.legacy_categories),
    path("category/<uslug:slug>/", views.legacy_category),
    path("author/<int:author_id>/", views.legacy_author),
    path("author/<int:author_id>/books/", views.legacy_author),
]
