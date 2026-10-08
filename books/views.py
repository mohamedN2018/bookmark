from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .forms import BookForm, CustomUserCreationForm, ProfileForm, ReviewForm
from .models import Author, Book, Bookmark, Category, ReadingHistory, Review, UserActivity

SEARCH_SUGGEST_LIMIT = 8


def _forbidden_json(message="ليس لديك صلاحية لهذا الإجراء."):
    return JsonResponse({"success": False, "message": message}, status=403)


def _safe_next_url(request, fallback):
    """يمنع open redirect: لا نعيد التوجيه إلا لمسار داخل نفس الموقع."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return reverse(fallback)


def _author_stats(authors):
    """إحصاءات حقيقية للمؤلفين باستعلام واحد بدل N+1."""
    return [
        {
            "author": author,
            "books_count": author.books_total,
            "readers_count": author.readers_total,
            "avg_rating": round(author.avg_rating or 0, 1),
            "avatar_url": author.avatar.url if author.avatar else None,
        }
        for author in authors
    ]


def _annotated_authors():
    return Author.objects.annotate(
        books_total=Count("books", distinct=True),
        readers_total=Count("books__readinghistory__user", distinct=True),
        avg_rating=Avg("books__reviews__rating"),
    )


def home(request):
    categories = Category.objects.annotate(books_count=Count("books"))

    featured_authors = _annotated_authors().filter(is_featured=True)[:4]
    if not featured_authors:
        featured_authors = _annotated_authors().order_by("-books_total")[:4]

    book_qs = Book.objects.select_related("author", "category")

    context = {
        "featured_books": book_qs.filter(is_featured=True)[:8],
        "latest_books": book_qs.order_by("-created_at")[:8],
        "top_rated_books": book_qs.annotate(avg_rating=Avg("reviews__rating"))
        .filter(avg_rating__gte=4)
        .order_by("-avg_rating")[:8],
        "categories": categories,
        # أرقام حقيقية من قاعدة البيانات فقط
        "count_book": Book.objects.count(),
        "count_author": Author.objects.count(),
        "count_book_cat": Category.objects.count(),
        "featured_authors": _author_stats(featured_authors),
    }
    return render(request, "home.html", context)


def all_authors(request):
    authors = Author.objects.annotate(books_count=Count("books")).order_by("-books_count", "name")

    search_query = request.GET.get("q", "").strip()
    if search_query:
        authors = authors.filter(
            Q(name__icontains=search_query) | Q(specialization__icontains=search_query) | Q(bio__icontains=search_query)
        )

    page_obj = Paginator(authors, 12).get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "total_authors": page_obj.paginator.count,
    }
    return render(request, "authors/list.html", context)


def author_books(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    books = Book.objects.filter(author=author).select_related("category").order_by("-created_at")
    page_obj = Paginator(books, 12).get_page(request.GET.get("page"))
    context = {
        "author": author,
        "page_obj": page_obj,
        "books_count": page_obj.paginator.count,
    }
    return render(request, "authors/books.html", context)


def author_detail(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    books = author.books.select_related("category")
    totals = books.aggregate(total_pages=Sum("pages"), total_downloads=Sum("downloads"), total_views=Sum("views"))
    context = {
        "author": author,
        "books": books,
        "featured_books": books.filter(is_featured=True)[:4],
        "total_pages": totals["total_pages"] or 0,
        "total_downloads": totals["total_downloads"] or 0,
        "total_views": totals["total_views"] or 0,
        "books_count": books.count(),
    }
    return render(request, "authors/detail.html", context)


def _search_books(queryset, query, extra=None):
    # مؤقت حتى المرحلة 4 (محرك البحث مع التطبيع العربي)
    condition = (
        Q(title__icontains=query)
        | Q(author__name__icontains=query)
        | Q(author_name__icontains=query)
        | Q(description__icontains=query)
    )
    if extra is not None:
        condition |= extra
    return queryset.filter(condition)


def book_list(request):
    books = Book.objects.select_related("author", "category").order_by("-created_at")

    category_slug = request.GET.get("category")
    current_category = None
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        books = books.filter(category=current_category)

    query = request.GET.get("q", "").strip()
    if query:
        books = _search_books(books, query)

    price_filter = request.GET.get("price")
    if price_filter == "free":
        books = books.filter(is_free=True)
    elif price_filter == "paid":
        books = books.filter(is_free=False)

    language = request.GET.get("language")
    if language:
        books = books.filter(language=language)

    books_page = Paginator(books, 12).get_page(request.GET.get("page"))

    context = {
        "books": books_page,
        "categories": Category.objects.all(),
        "languages": Book.objects.order_by().values_list("language", flat=True).distinct(),
        "current_category": current_category,
        "current_query": query,
        "current_price": price_filter,
        "current_language": language,
        "free_books_count": Book.objects.filter(is_free=True).count(),
        "featured_books_count": Book.objects.filter(is_featured=True).count(),
        "categories_count": Category.objects.count(),
        "total_results": books_page.paginator.count,
    }
    return render(request, "books/list.html", context)


@require_GET
def search_suggest(request):
    """اقتراحات البحث في الشريط العلوي (بيانات حقيقية؛ الواجهة تعرضها كنص وليس HTML)."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})
    books = _search_books(Book.objects.select_related("author"), query)[:SEARCH_SUGGEST_LIMIT]
    results = [
        {
            "title": b.title,
            "author": b.author.name if b.author else (b.author_name or ""),
            "url": b.get_absolute_url(),
        }
        for b in books
    ]
    return JsonResponse({"results": results})


def book_detail(request, slug):
    book = get_object_or_404(Book.objects.select_related("author", "category"), slug=slug)
    book.increment_views()

    reviews = book.reviews.select_related("user").order_by("-created_at")
    similar_books = Book.objects.filter(category=book.category).exclude(id=book.id).select_related("author")[:4]

    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(user=request.user, book=book).exists()
        # تسجيل الزيارة دون المساس بالتقدم المحفوظ
        history, created = ReadingHistory.objects.get_or_create(user=request.user, book=book)
        if not created:
            history.save(update_fields=["last_read"])

    ratings_map = {r["rating"]: r["count"] for r in book.reviews.values("rating").annotate(count=Count("id"))}
    ratings_data = [{"stars": i, "count": ratings_map.get(i, 0)} for i in range(5, 0, -1)]

    context = {
        "book": book,
        "reviews": reviews,
        "similar_books": similar_books,
        "is_bookmarked": is_bookmarked,
        "review_form": ReviewForm(),
        "ratings_data": ratings_data,
        "total_reviews": sum(ratings_map.values()),
    }
    return render(request, "books/detail.html", context)


def categories_list(request):
    categories = Category.objects.annotate(
        books_count=Count("books", distinct=True),
        avg_rating=Avg("books__reviews__rating"),
        authors_count=Count("books__author", distinct=True),
    ).order_by("-books_count")

    month_ago = timezone.now() - timedelta(days=30)
    recent_categories = (
        Category.objects.annotate(recent_books=Count("books", filter=Q(books__created_at__gte=month_ago)))
        .filter(recent_books__gt=0)
        .order_by("-recent_books")[:6]
    )

    context = {
        "categories": categories,
        "popular_categories": categories[:8],
        "recent_categories": recent_categories,
        "total_books": Book.objects.count(),
        "total_categories": Category.objects.count(),
        "total_authors": Author.objects.filter(books__isnull=False).distinct().count(),
    }
    return render(request, "books/categories_list.html", context)


@login_required
@require_POST
def add_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    form = ReviewForm(request.POST)
    if form.is_valid():
        Review.objects.update_or_create(
            book=book,
            user=request.user,
            defaults={
                "rating": form.cleaned_data["rating"],
                "comment": form.cleaned_data["comment"],
            },
        )
        messages.success(request, "تم حفظ تقييمك بنجاح")
    else:
        messages.error(request, "حدث خطأ في التقييم")
    return redirect("book_detail", slug=book.slug)


@login_required
@require_POST
def toggle_bookmark(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, book=book)
    if not created:
        bookmark.delete()
    return JsonResponse({"bookmarked": created, "book_id": book_id})


def books_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    books = Book.objects.filter(category=category).select_related("author").order_by("-created_at")
    features = [f.strip() for f in category.features.split(",") if f.strip()] if category.features else []

    page_obj = Paginator(books, 12).get_page(request.GET.get("page"))
    context = {
        "category": category,
        "page_obj": page_obj,
        "features": features,
    }
    return render(request, "books/category.html", context)


def _monthly_stats(months=6):
    """إحصاءات شهرية حقيقية باستعلامين بدل 12 استعلامًا."""
    today = timezone.localdate()
    keys = []
    year, month = today.year, today.month
    for _ in range(months):
        keys.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    keys.reverse()
    start = timezone.make_aware(datetime(keys[0][0], keys[0][1], 1))

    def counts(qs, field):
        rows = qs.filter(**{f"{field}__gte": start}).annotate(m=TruncMonth(field)).values("m").annotate(c=Count("id"))
        return {(r["m"].year, r["m"].month): r["c"] for r in rows}

    books = counts(Book.objects.all(), "created_at")
    users = counts(User.objects.all(), "date_joined")
    return [{"month": m, "year": y, "books": books.get((y, m), 0), "users": users.get((y, m), 0)} for y, m in keys]


def _today_visitors():
    today = timezone.localdate()
    visitors = UserActivity.objects.filter(visited_at__date=today).values("user").distinct().count()
    if visitors == 0:
        visitors = ReadingHistory.objects.filter(last_read__date=today).values("user").distinct().count()
    return visitors


@login_required
def dashboard(request):
    user = request.user
    history = ReadingHistory.objects.filter(user=user).select_related("book")

    # وقت القراءة الحقيقي المسجّل فقط؛ لا نشتقه من نسب التقدم
    total_minutes = history.aggregate(total=Sum("reading_duration_minutes"))["total"] or 0

    context = {
        "bookmarks_count": Bookmark.objects.filter(user=user).count(),
        "total_reading_time": total_minutes / 60,
        "reviews_count": Review.objects.filter(user=user).count(),
        "reading_history": history.order_by("-last_read")[:10],
        "recent_books": history.order_by("-last_read")[:6],
    }

    if user.is_staff:
        context.update(
            {
                "total_books": Book.objects.count(),
                "total_users": User.objects.filter(is_active=True).count(),
                "total_reviews": Review.objects.count(),
                "today_visitors": _today_visitors(),
                "avg_rating": round(Review.objects.aggregate(avg=Avg("rating"))["avg"] or 0, 1),
                "monthly_stats": _monthly_stats(),
            }
        )

    return render(request, "dashboard/index.html", context)


@login_required
@require_GET
def get_statistics(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "غير مصرح"}, status=403)

    now = timezone.now()
    return JsonResponse(
        {
            "success": True,
            "stats": {
                "total_books": Book.objects.count(),
                "total_users": User.objects.filter(is_active=True).count(),
                "total_reviews": Review.objects.count(),
                "today_visitors": _today_visitors(),
                "monthly_books": Book.objects.filter(created_at__year=now.year, created_at__month=now.month).count(),
                "monthly_users": User.objects.filter(date_joined__year=now.year, date_joined__month=now.month).count(),
            },
        }
    )


def _staff_required_page(request):
    if not request.user.is_staff:
        messages.error(request, "ليس لديك صلاحية للوصول إلى هذه الصفحة.")
        return redirect("dashboard")
    return None


@login_required
def dashboard_users(request):
    if (denied := _staff_required_page(request)) is not None:
        return denied

    users = User.objects.all().order_by("-date_joined")

    search_query = request.GET.get("search", "").strip()
    role_filter = request.GET.get("role", "")

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )

    if role_filter == "staff":
        users = users.filter(is_staff=True)
    elif role_filter == "active":
        users = users.filter(is_active=True)
    elif role_filter == "inactive":
        users = users.filter(is_active=False)

    context = {
        "page_obj": Paginator(users, 15).get_page(request.GET.get("page")),
        "search_query": search_query,
        "role_filter": role_filter,
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
        "today_users": User.objects.filter(date_joined__date=timezone.localdate()).count(),
    }
    return render(request, "dashboard/users.html", context)


@login_required
def dashboard_settings(request):
    if (denied := _staff_required_page(request)) is not None:
        return denied

    if request.method == "POST":
        # لا نعرض رسالة نجاح لعملية لم تُنفّذ
        messages.warning(request, "لم يُحفظ شيء: هذه الإعدادات غير مفعّلة بعد.")
        return redirect("dashboard_settings")

    return render(request, "dashboard/settings.html", {})


@login_required
def dashboard_books(request):
    if (denied := _staff_required_page(request)) is not None:
        return denied

    books = Book.objects.select_related("author", "category")

    search_query = request.GET.get("search", "").strip()
    category_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "-created_at")

    if search_query:
        books = _search_books(books, search_query, extra=Q(category__name__icontains=search_query))

    if category_filter.isdigit():
        books = books.filter(category_id=category_filter)

    if status_filter == "free":
        books = books.filter(is_free=True)
    elif status_filter == "paid":
        books = books.filter(is_free=False)
    elif status_filter == "featured":
        books = books.filter(is_featured=True)

    if sort_by not in ["title", "-title", "-created_at", "-views", "-downloads"]:
        sort_by = "-created_at"
    books = books.order_by(sort_by)

    editing_book = None
    edit_id = request.GET.get("edit")
    if edit_id and edit_id.isdigit():
        editing_book = Book.objects.filter(id=edit_id).first()
        if editing_book is None:
            messages.error(request, "الكتاب المطلوب غير موجود.")

    if request.method == "POST":
        book_id = request.POST.get("book_id")
        instance = None
        if book_id:
            instance = Book.objects.filter(id=book_id).first()
            if instance is None:
                messages.error(request, "الكتاب المطلوب غير موجود.")
                return redirect("dashboard_books")
        form = BookForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            book = form.save()
            verb = "تحديث" if instance else "إضافة"
            messages.success(request, f'تم {verb} الكتاب "{book.title}" بنجاح!')
            return redirect("dashboard_books")
        errors = "؛ ".join(f"{field}: {', '.join(errs)}" for field, errs in form.errors.items())
        messages.error(request, f"لم يتم الحفظ. {errors}")

    context = {
        "books": Paginator(books, 10).get_page(request.GET.get("page")),
        "categories": Category.objects.all(),
        "authors": Author.objects.all(),
        "search_query": search_query,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "sort_by": sort_by,
        "editing_book": editing_book,
        "free_books_count": Book.objects.filter(is_free=True).count(),
        "featured_books_count": Book.objects.filter(is_featured=True).count(),
        "categories_count": Category.objects.count(),
    }
    return render(request, "dashboard/manage_books.html", context)


@login_required
@require_POST
def delete_book(request, book_id):
    if not request.user.is_staff:
        return _forbidden_json()

    book = Book.objects.filter(id=book_id).first()
    if book is None:
        return JsonResponse({"success": False, "message": "الكتاب المطلوب غير موجود."}, status=404)
    title = book.title
    book.delete()
    return JsonResponse({"success": True, "message": f'تم حذف الكتاب "{title}" بنجاح.'})


def _can_manage_user(actor, target):
    """قواعد إدارة المستخدمين:
    - لا أحد يعدّل حسابه بنفسه من هنا.
    - حسابات المدير العام (superuser) لا يعدّلها إلا مدير عام.
    """
    if actor.pk == target.pk:
        return False
    if target.is_superuser and not actor.is_superuser:
        return False
    return True


@login_required
@require_POST
def toggle_user_status(request, user_id):
    if not request.user.is_staff:
        return _forbidden_json()

    target = get_object_or_404(User, id=user_id)
    if not _can_manage_user(request.user, target):
        return _forbidden_json("لا يمكنك تعديل هذا الحساب.")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    status = "تفعيل" if target.is_active else "تعطيل"
    return JsonResponse(
        {"success": True, "message": f'تم {status} المستخدم "{target.username}".', "is_active": target.is_active}
    )


@login_required
@require_POST
def toggle_staff_status(request, user_id):
    # منح/سحب صلاحيات الإدارة للمدير العام فقط (منع تصعيد الصلاحيات)
    if not request.user.is_superuser:
        return _forbidden_json("منح صلاحيات الإدارة متاح للمدير العام فقط.")

    target = get_object_or_404(User, id=user_id)
    if not _can_manage_user(request.user, target):
        return _forbidden_json("لا يمكنك تعديل هذا الحساب.")

    target.is_staff = not target.is_staff
    target.save(update_fields=["is_staff"])
    status = "منح" if target.is_staff else "سحب"
    return JsonResponse(
        {
            "success": True,
            "message": f'تم {status} صلاحيات الإدارة للمستخدم "{target.username}".',
            "is_staff": target.is_staff,
        }
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "تم إنشاء حسابك بنجاح! مرحباً بك.")
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()

    return render(request, "auth/register.html", {"form": form, "title": "إنشاء حساب جديد"})


def _login_failure_key(username):
    return f"login-failures:{(username or '').strip().lower()}"


def user_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        # حماية من التخمين: حد للمحاولات الفاشلة لكل اسم مستخدم
        key = _login_failure_key(request.POST.get("username"))
        if cache.get(key, 0) >= settings.LOGIN_MAX_FAILURES:
            messages.error(request, "محاولات كثيرة غير ناجحة. حاول مرة أخرى بعد قليل.")
            form = AuthenticationForm(request)
            return render(request, "auth/login.html", {"form": form, "title": "تسجيل الدخول"}, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            cache.delete(key)
            user = form.get_user()
            login(request, user)
            if not request.POST.get("remember-me"):
                # تنتهي الجلسة عند إغلاق المتصفح
                request.session.set_expiry(0)
            messages.success(request, f"مرحباً بك مرة أخرى {user.get_username()}!")
            return redirect(_safe_next_url(request, "dashboard"))
        cache.add(key, 0, settings.LOGIN_FAILURE_WINDOW_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, settings.LOGIN_FAILURE_WINDOW_SECONDS)
        messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
    else:
        form = AuthenticationForm()

    return render(request, "auth/login.html", {"form": form, "title": "تسجيل الدخول"})


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect("home")


@login_required
@require_POST
def delete_account(request):
    """حذف الحساب فعليًا بعد تأكيد كلمة المرور. المدير العام لا يحذف حسابه من هنا."""
    user = request.user
    if user.is_superuser:
        messages.error(request, "لا يمكن حذف حساب المدير العام من هذه الصفحة.")
        return redirect("profile")
    if not user.check_password(request.POST.get("password", "")):
        messages.error(request, "كلمة المرور غير صحيحة. لم يتم حذف الحساب.")
        return redirect("profile")
    logout(request)
    user.delete()
    messages.success(request, "تم حذف حسابك وكل بياناته.")
    return redirect("home")


@login_required
def profile(request):
    user = request.user

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            if form.cleaned_data.get("new_password"):
                # يبقي المستخدم مسجلًا بعد تغيير كلمة المرور
                update_session_auth_hash(request, user)
            messages.success(request, "تم تحديث الملف الشخصي بنجاح.")
            return redirect("profile")
        for errs in form.errors.values():
            for err in errs:
                messages.error(request, err)
        return redirect("profile")

    context = {
        "reading_history_count": ReadingHistory.objects.filter(user=user).count(),
        "bookmarks_count": Bookmark.objects.filter(user=user).count(),
        "reviews_count": Review.objects.filter(user=user).count(),
    }
    return render(request, "auth/profile.html", context)
