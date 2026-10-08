from django.urls import path, register_converter

from core.converters import UnicodeSlugConverter

from . import views

register_converter(UnicodeSlugConverter, "uslug")

urlpatterns = [
    # الصفحات العامة
    path("", views.home, name="home"),
    path("books/", views.book_list, name="book_list"),
    path("books/<uslug:slug>/", views.book_detail, name="book_detail"),
    path("categories/", views.categories_list, name="categories_list"),
    path("category/<uslug:slug>/", views.books_by_category, name="books_by_category"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    # المؤلفون
    path("authors/", views.all_authors, name="all_authors"),
    path("author/<int:author_id>/books/", views.author_books, name="author_books"),
    path("author/<int:author_id>/", views.author_detail, name="author_detail"),
    # المصادقة
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/delete/", views.delete_account, name="delete_account"),
    # لوحة التحكم
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/books/", views.dashboard_books, name="dashboard_books"),
    path("dashboard/users/", views.dashboard_users, name="dashboard_users"),
    path("dashboard/settings/", views.dashboard_settings, name="dashboard_settings"),
    path("dashboard/statistics/", views.get_statistics, name="get_statistics"),
    # AJAX
    path("dashboard/books/<int:book_id>/delete/", views.delete_book, name="delete_book"),
    path("dashboard/users/<int:user_id>/toggle-status/", views.toggle_user_status, name="toggle_user_status"),
    path("dashboard/users/<int:user_id>/toggle-staff/", views.toggle_staff_status, name="toggle_staff_status"),
    path("books/<int:book_id>/review/", views.add_review, name="add_review"),
    path("books/<int:book_id>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
]
