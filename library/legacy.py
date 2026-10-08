"""نقل بيانات المستخدمين من النموذج القديم (books) إلى library.

يعتمد على Work.legacy_book، لذا يجب نقل الكتب أولًا (catalog.legacy).
آمن للتكرار: get_or_create لكل سجل.
"""


def import_legacy_user_data(apps):
    Work = apps.get_model("catalog", "Work")
    Bookmark = apps.get_model("books", "Bookmark")
    Review = apps.get_model("books", "Review")
    ReadingHistory = apps.get_model("books", "ReadingHistory")
    SavedWork = apps.get_model("library", "SavedWork")
    Rating = apps.get_model("library", "Rating")
    ReadingEntry = apps.get_model("library", "ReadingEntry")

    work_by_book = dict(Work.objects.filter(legacy_book__isnull=False).values_list("legacy_book_id", "id"))
    counts = {"saved": 0, "ratings": 0, "history": 0}

    for bookmark in Bookmark.objects.all():
        work_id = work_by_book.get(bookmark.book_id)
        if work_id:
            _, created = SavedWork.objects.get_or_create(user_id=bookmark.user_id, work_id=work_id)
            counts["saved"] += created

    for review in Review.objects.all():
        work_id = work_by_book.get(review.book_id)
        if work_id:
            _, created = Rating.objects.get_or_create(
                user_id=review.user_id,
                work_id=work_id,
                defaults={"score": review.rating, "comment": review.comment or ""},
            )
            counts["ratings"] += created

    for entry in ReadingHistory.objects.all():
        work_id = work_by_book.get(entry.book_id)
        if work_id:
            _, created = ReadingEntry.objects.get_or_create(user_id=entry.user_id, work_id=work_id)
            counts["history"] += created

    return counts
