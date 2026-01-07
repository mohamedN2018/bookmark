from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # الصفحات العامة
    path('', views.home, name='home'),
    path('books/', views.book_list, name='book_list'),
    path('books/<slug:slug>/', views.book_detail, name='book_detail'),
    path('category/<slug:slug>/', views.books_by_category, name='books_by_category'),
    
    # المصادقة
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # مسارات لوحة التحكم
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/books/', views.dashboard_books, name='dashboard_books'),
    path('dashboard/users/', views.dashboard_users, name='dashboard_users'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
    
    # مسارات AJAX
    path('dashboard/books/<int:book_id>/delete/', views.delete_book, name='delete_book'),
    path('dashboard/users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('dashboard/users/<int:user_id>/toggle-staff/', views.toggle_staff_status, name='toggle_staff_status'),
    path('dashboard/statistics/', views.get_statistics, name='get_statistics'),

    # API
    # path('api/search/', views.search_books, name='search_books'),
    path('books/<int:book_id>/review/', views.add_review, name='add_review'),
    path('books/<int:book_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
]