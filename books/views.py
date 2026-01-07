from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm, ReviewForm, BookForm
from .models import Book, Category, Review, Bookmark, ReadingHistory
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json
from django.utils import timezone
from django.db import models
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

def home(request):
    # الكتب المميزة
    featured_books = Book.objects.filter(is_featured=True)[:8]
    
    # أحدث الكتب
    latest_books = Book.objects.all().order_by('-created_at')[:8]
    
    # أكثر الكتب تقييماً
    top_rated_books = Book.objects.annotate(
        avg_rating=Avg('reviews__rating')
    ).filter(avg_rating__gte=4).order_by('-avg_rating')[:8]
    
    context = {
        'featured_books': featured_books,
        'latest_books': latest_books,
        'top_rated_books': top_rated_books,
    }
    return render(request, 'home.html', context)

def book_list(request):
    books = Book.objects.all().order_by('-created_at')
    featured_books = Book.objects.filter(is_featured=True)[:8]

    # ===== التصفية حسب التصنيف =====
    category_slug = request.GET.get('category')
    current_category = None
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        books = books.filter(category=current_category)
    
    # ===== البحث =====
    query = request.GET.get('q')
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(description__icontains=query)
        )
    
    # ===== التصفية حسب السعر =====
    price_filter = request.GET.get('price')
    if price_filter == 'free':
        books = books.filter(is_free=True)
    elif price_filter == 'paid':
        books = books.filter(is_free=False)
    
    # ===== التصفية حسب اللغة =====
    language = request.GET.get('language')
    if language:
        books = books.filter(language=language)
    
    # ===== الترقيم =====
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    context = {
        'books': books,
        'categories': Category.objects.all(),
        'languages': Book.objects.values_list('language', flat=True).distinct(),
        'current_category': current_category,  # <--- أضفنا هذا
        'current_query': query,
        'current_price': price_filter,
        'current_language': language,
        'featured_books': featured_books,
    }
    
    return render(request, 'books/list.html', context)

def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug)
    books = Book.objects.all()
    reviews = book.reviews.all().order_by('-created_at')
    similar_books = Book.objects.filter(
        category=book.category
    ).exclude(id=book.id)[:4]

    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(
            user=request.user,
            book=book
        ).exists()

        ReadingHistory.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={'progress': 0}
        )

    # ✅ تجهيز توزيع التقييمات
    ratings_qs = (
        book.reviews
        .values('rating')
        .annotate(count=Count('id'))
    )

    ratings_map = {r['rating']: r['count'] for r in ratings_qs}

    ratings_data = []
    for i in range(5, 0, -1):
        ratings_data.append({
            'stars': i,
            'count': ratings_map.get(i, 0)
        })

    total_reviews = book.reviews.count()

    context = {
        'book': book,
        'reviews': reviews,
        'similar_books': similar_books,
        'is_bookmarked': is_bookmarked,
        'review_form': ReviewForm(),
        'ratings_data': ratings_data,
        'total_reviews': total_reviews,
        'books': books,
    }

    return render(request, 'books/detail.html', context)


@login_required
def add_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.update_or_create(
                book=book,
                user=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'comment': form.cleaned_data['comment'],
                }
            )
            messages.success(request, 'تم حفظ تقييمك بنجاح')
        else:
            messages.error(request, 'حدث خطأ في التقييم')

    return redirect('book_detail', slug=book.slug)


@login_required
@require_POST
def toggle_bookmark(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user,
        book=book
    )
    
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True
    
    return JsonResponse({'bookmarked': bookmarked, 'book_id': book_id})

def books_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    books = Book.objects.filter(category=category).order_by('-created_at')
    features = category.features.split(",") if category.features else []

    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
        'features': features,
    }
    return render(request, 'books/category.html', context)

@login_required
def dashboard(request):
    user = request.user
    
    # إحصائيات عامة للمستخدم
    bookmarks_count = Bookmark.objects.filter(user=user).count()
    
    # حساب وقت القراءة الكلي
    total_reading_time = ReadingHistory.objects.filter(
        user=user
    ).aggregate(
        total_time=Sum('reading_duration_minutes')
    )['total_time'] or 0
    
    # إذا لم يكن هناك حقل reading_duration_minutes في النموذج، يمكننا استخدام التقدم كنسبة مئوية
    # أو نعتبر أن كل 1% تقدم = دقيقة واحدة (كمثال افتراضي)
    if total_reading_time == 0:
        # استخدم التقدم كنسبة مئوية واعتبرها دقائق (للتوضيح فقط)
        total_reading_time = ReadingHistory.objects.filter(
            user=user
        ).aggregate(
            total_progress=Sum('progress')
        )['total_progress'] or 0
    
    reviews_count = Review.objects.filter(user=user).count()
    
    # تاريخ القراءة (آخر 10 سجلات)
    reading_history = ReadingHistory.objects.filter(
        user=user
    ).select_related('book').order_by('-last_read')[:10]
    
    # الكتب المقروءة مؤخراً (آخر 6 كتب للعرض)
    recent_books = ReadingHistory.objects.filter(
        user=user
    ).select_related('book').order_by('-last_read')[:6]
    
    context = {
        'bookmarks_count': bookmarks_count,
        'total_reading_time': total_reading_time / 60 if total_reading_time > 0 else 0,  # تحويل إلى ساعات
        'reviews_count': reviews_count,
        'reading_history': reading_history,
        'recent_books': recent_books,
    }
    
    # إحصائيات إضافية للـ staff
    if user.is_staff:
        # احصائيات إدارية
        today = timezone.now().date()
        today_visitors = UserActivity.objects.filter(
            visited_at__date=today
        ).values('user').distinct().count()
        
        # إذا لم يكن هناك نموذج UserActivity، يمكن استخدام ReadingHistory
        if today_visitors == 0:
            today_visitors = ReadingHistory.objects.filter(
                last_read__date=today
            ).values('user').distinct().count()
        
        total_books = Book.objects.count()
        total_users = User.objects.filter(is_active=True).count()
        total_reviews = Review.objects.count()
        
        # حساب متوسط التقييمات
        avg_rating = Review.objects.aggregate(
            avg=Avg('rating')
        )['avg'] or 0
        
        # إحصائيات الشهور الستة الماضية
        monthly_stats = []
        for i in range(5, -1, -1):
            target_date = timezone.now() - timedelta(days=30*i)
            month = target_date.month
            year = target_date.year
            
            # كتب هذا الشهر
            month_books = Book.objects.filter(
                created_at__month=month,
                created_at__year=year
            ).count()
            
            # مستخدمين جدد هذا الشهر
            month_users = User.objects.filter(
                date_joined__month=month,
                date_joined__year=year
            ).count()
            
            monthly_stats.append({
                'month': month,
                'year': year,
                'books': month_books,
                'users': month_users,
            })
        
        context.update({
            'total_books': total_books,
            'total_users': total_users,
            'total_reviews': total_reviews,
            'today_visitors': today_visitors,
            'avg_rating': round(avg_rating, 1),
            'monthly_stats': monthly_stats,
        })
    
    return render(request, 'dashboard/index.html', context)


# إضافة نموذج UserActivity إذا لم يكن موجوداً
class UserActivity(models.Model):
    """نموذج لتتبع نشاط المستخدمين"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=[
        ('login', 'تسجيل دخول'),
        ('view_book', 'عرض كتاب'),
        ('read_book', 'قراءة كتاب'),
        ('review', 'إضافة تقييم'),
        ('bookmark', 'إضافة إشارة مرجعية'),
    ])
    details = models.TextField(blank=True, null=True)
    visited_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "نشاط المستخدم"
        verbose_name_plural = "أنشطة المستخدمين"
        ordering = ['-visited_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.visited_at}"


# view للاستعلام AJAX لتحديث الإحصائيات
@login_required
def get_statistics(request):
    """API للحصول على إحصائيات محدثة"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'غير مصرح'}, status=403)
    
    try:
        today = timezone.now().date()
        
        # احصائيات اليوم
        today_visitors = UserActivity.objects.filter(
            visited_at__date=today
        ).values('user').distinct().count()
        
        if today_visitors == 0:
            today_visitors = ReadingHistory.objects.filter(
                last_read__date=today
            ).values('user').distinct().count()
        
        # إحصائيات عامة
        total_books = Book.objects.count()
        total_users = User.objects.filter(is_active=True).count()
        total_reviews = Review.objects.count()
        
        # إحصائيات الشهر الحالي
        current_month = timezone.now().month
        current_year = timezone.now().year
        
        monthly_books = Book.objects.filter(
            created_at__month=current_month,
            created_at__year=current_year
        ).count()
        
        monthly_users = User.objects.filter(
            date_joined__month=current_month,
            date_joined__year=current_year
        ).count()
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_books': total_books,
                'total_users': total_users,
                'total_reviews': total_reviews,
                'today_visitors': today_visitors,
                'monthly_books': monthly_books,
                'monthly_users': monthly_users,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
    user = request.user
    
    # إحصائيات عامة للمستخدم
    reading_history = (
        ReadingHistory.objects
        .filter(user=user)
        .order_by('-last_read')[:5]
    )

    bookmarks_count = Bookmark.objects.filter(user=user).count()
    reviews_count = Review.objects.filter(user=user).count()
    
    # إحصائيات القراءة
    total_reading_time = (
        ReadingHistory.objects
        .filter(user=user)
        .aggregate(total_time=Sum('progress'))
        .get('total_time') or 0
    )
    
    # الكتب المقروءة مؤخراً
    recent_books = (
        ReadingHistory.objects
        .filter(user=user)
        .select_related('book')
        .order_by('-last_read')[:6]
    )
    
    context = {
        'reading_history': reading_history,
        'bookmarks_count': bookmarks_count,
        'reviews_count': reviews_count,
        'total_reading_time': total_reading_time,
        'recent_books': recent_books,
    }
    
    # إحصائيات إضافية للـ staff
    if user.is_staff:
        today_visitors = (
            ReadingHistory.objects
            .filter(last_read__date=datetime.now().date())
            .values('user')
            .distinct()
            .count()
        )

        context.update({
            'total_books': Book.objects.count(),
            'total_users': User.objects.count(),
            'total_reviews': Review.objects.count(),
            'today_visitors': today_visitors,
        })
    
    return render(request, 'dashboard/index.html', context)


@login_required
def dashboard_books(request):
    # التحقق من صلاحيات الموظفين
    if not request.user.is_staff:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة.')
        return redirect('dashboard')
    
    books = Book.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        books = books.filter(category_id=category_filter)
    
    if status_filter:
        if status_filter == 'free':
            books = books.filter(is_free=True)
        elif status_filter == 'paid':
            books = books.filter(is_free=False)
        elif status_filter == 'featured':
            books = books.filter(is_featured=True)
    
    # الترقيم
    paginator = Paginator(books, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'تم إضافة الكتاب "{book.title}" بنجاح!')
            return redirect('dashboard_books')
        else:
            messages.error(request, 'حدث خطأ أثناء إضافة الكتاب. يرجى التحقق من البيانات.')
    else:
        form = BookForm()
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'books_count': books.count(),
    }
    return render(request, 'dashboard/books.html', context)

@login_required
def dashboard_users(request):
    # التحقق من صلاحيات الموظفين
    if not request.user.is_staff:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة.')
        return redirect('dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if role_filter:
        if role_filter == 'staff':
            users = users.filter(is_staff=True)
        elif role_filter == 'active':
            users = users.filter(is_active=True)
        elif role_filter == 'inactive':
            users = users.filter(is_active=False)
    
    # الترقيم
    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات المستخدمين
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()
    today_users = User.objects.filter(
        date_joined__date=datetime.now().date()
    ).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
        'today_users': today_users,
    }
    return render(request, 'dashboard/users.html', context)

@login_required
def dashboard_settings(request):
    # التحقق من صلاحيات الموظفين
    if not request.user.is_staff:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'general':
            # حفظ الإعدادات العامة
            messages.success(request, 'تم حفظ الإعدادات العامة بنجاح!')
            
        elif action == 'appearance':
            # حفظ إعدادات المظهر
            messages.success(request, 'تم حفظ إعدادات المظهر بنجاح!')
            
        elif action == 'notifications':
            # حفظ إعدادات الإشعارات
            messages.success(request, 'تم حفظ إعدادات الإشعارات بنجاح!')
            
        elif action == 'backup':
            # إنشاء نسخة احتياطية
            messages.success(request, 'تم إنشاء النسخة الاحتياطية بنجاح!')
        
        return redirect('dashboard_settings')
    
    # إحصائيات النظام
    total_storage = Book.objects.aggregate(
        total=Sum('pages')
    )['total'] or 0
    
    context = {
        'total_storage': total_storage,
    }
    return render(request, 'dashboard/settings.html', context)

@login_required
@require_POST
def delete_book(request, book_id):
    # التحقق من صلاحيات الموظفين
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية لهذا الإجراء.'})
    
    book = get_object_or_404(Book, id=book_id)
    book_title = book.title
    book.delete()
    
    return JsonResponse({'success': True, 'message': f'تم حذف الكتاب "{book_title}" بنجاح.'})

@login_required
@require_POST
def toggle_user_status(request, user_id):
    # التحقق من صلاحيات الموظفين
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية لهذا الإجراء.'})
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    status = "مفعل" if user.is_active else "معطل"
    return JsonResponse({'success': True, 'message': f'تم {status} المستخدم "{user.username}" بنجاح.', 'is_active': user.is_active})

@login_required
@require_POST
def toggle_staff_status(request, user_id):
    # التحقق من صلاحيات الموظفين
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية لهذا الإجراء.'})
    
    user = get_object_or_404(User, id=user_id)
    user.is_staff = not user.is_staff
    user.save()
    
    status = "منح" if user.is_staff else "سحب"
    return JsonResponse({'success': True, 'message': f'تم {status} صلاحيات الموظف للمستخدم "{user.username}" بنجاح.', 'is_staff': user.is_staff})

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # تسجيل الدخول تلقائياً بعد التسجيل
            login(request, user)
            messages.success(request, 'تم إنشاء حسابك بنجاح! مرحباً بك.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'إنشاء حساب جديد'
    }
    return render(request, 'auth/register.html', context)

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'مرحباً بك مرة أخرى {username}!')
                
                # إعادة توجيه إلى الصفحة التي حاول الوصول إليها أو إلى لوحة التحكم
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'title': 'تسجيل الدخول'
    }
    return render(request, 'auth/login.html', context)


def user_logout(request):
    logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('home')

@login_required
def profile(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        # تحديث بيانات المستخدم
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        # تحديث كلمة المرور إذا تم تقديمها
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        
        user.save()
        messages.success(request, 'تم تحديث الملف الشخصي بنجاح.')
        return redirect('profile')
    
    # جلب إحصائيات المستخدم
    reading_history = ReadingHistory.objects.filter(user=request.user).count()
    bookmarks_count = Bookmark.objects.filter(user=request.user).count()
    reviews_count = Review.objects.filter(user=request.user).count()
    
    context = {
        'reading_history_count': reading_history,
        'bookmarks_count': bookmarks_count,
        'reviews_count': reviews_count,
    }
    return render(request, 'auth/profile.html', context)

@login_required
def custom_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'تم تسجيل الخروج بنجاح.')
        return redirect('home')
    return redirect('home')