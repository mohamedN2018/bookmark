from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CustomUserCreationForm, ProfileForm


def _safe_next_url(request, fallback):
    """يمنع open redirect: لا نعيد التوجيه إلا لمسار داخل نفس الموقع."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return reverse(fallback)


def _login_failure_key(username):
    return f"login-failures:{(username or '').strip().lower()}"


def user_login(request):
    if request.user.is_authenticated:
        return redirect("my_library")

    status = 200
    if request.method == "POST":
        key = _login_failure_key(request.POST.get("username"))
        if cache.get(key, 0) >= settings.LOGIN_MAX_FAILURES:
            messages.error(request, "محاولات كثيرة غير ناجحة. حاول مرة أخرى بعد قليل.")
            return render(request, "accounts/login.html", {"form": AuthenticationForm(request)}, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            cache.delete(key)
            user = form.get_user()
            login(request, user)
            if not request.POST.get("remember-me"):
                request.session.set_expiry(0)
            return redirect(_safe_next_url(request, "my_library"))
        cache.add(key, 0, settings.LOGIN_FAILURE_WINDOW_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, settings.LOGIN_FAILURE_WINDOW_SECONDS)
        messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
        status = 400
    else:
        form = AuthenticationForm(request)
    return render(request, "accounts/login.html", {"form": form}, status=status)


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج.")
    return redirect("home")


def register(request):
    if request.user.is_authenticated:
        return redirect("my_library")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "تم إنشاء حسابك.")
            return redirect("my_library")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    user = request.user
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            if form.cleaned_data.get("new_password"):
                update_session_auth_hash(request, user)
            messages.success(request, "تم حفظ التعديلات.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
@require_POST
def delete_account(request):
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
