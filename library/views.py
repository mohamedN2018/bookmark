from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Work
from catalog.views import _work_list_qs

from .forms import RatingForm
from .models import Rating, ReadingEntry, SavedWork


@login_required
@require_POST
def toggle_save(request, work_id):
    work = get_object_or_404(Work, pk=work_id)
    saved, created = SavedWork.objects.get_or_create(user=request.user, work=work)
    if not created:
        saved.delete()
    if request.headers.get("Accept", "").startswith("application/json"):
        return JsonResponse({"saved": created})
    return redirect(work.get_absolute_url())


@login_required
@require_POST
def rate(request, work_id):
    work = get_object_or_404(Work, pk=work_id)
    instance = Rating.objects.filter(user=request.user, work=work).first()
    form = RatingForm(request.POST, instance=instance)
    if form.is_valid():
        rating = form.save(commit=False)
        rating.user = request.user
        rating.work = work
        rating.save()
        messages.success(request, "تم حفظ تقييمك.")
    else:
        messages.error(request, "التقييم يجب أن يكون من 1 إلى 5.")
    return redirect(work.get_absolute_url() + "#ratings")


def _ordered_works(ids):
    """يعيد الأعمال بنفس ترتيب المعرّفات المعطاة."""
    position = {work_id: index for index, work_id in enumerate(ids)}
    works = _work_list_qs(Work.objects.filter(id__in=position))
    return sorted(works, key=lambda w: position[w.id])


@login_required
def my_library(request):
    user = request.user
    saved_ids = list(SavedWork.objects.filter(user=user).order_by("-created_at").values_list("work_id", flat=True))
    recent_ids = list(
        ReadingEntry.objects.filter(user=user).order_by("-last_opened_at").values_list("work_id", flat=True)[:12]
    )
    context = {
        "saved": _ordered_works(saved_ids),
        "recent": _ordered_works(recent_ids),
        "ratings": Rating.objects.filter(user=user).select_related("work"),
    }
    return render(request, "library/my_library.html", context)
