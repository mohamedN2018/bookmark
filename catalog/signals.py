"""تحديث فهرس البحث تلقائيًا عند تغيّر بيانات العمل."""

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .indexing import index_works, indexing_suspended
from .models import Contribution, Edition, Work


def _schedule(work_id):
    # فوري (داخل نفس المعاملة): كل حفظ لاحق لمؤلف/موضوع/طبعة يعيد الفهرسة
    if work_id and not indexing_suspended():
        index_works([work_id])


@receiver(post_save, sender=Work)
def work_saved(sender, instance, **kwargs):
    _schedule(instance.pk)


@receiver(m2m_changed, sender=Work.subjects.through)
def work_subjects_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"} and isinstance(instance, Work):
        _schedule(instance.pk)


@receiver([post_save, post_delete], sender=Contribution)
def contribution_changed(sender, instance, **kwargs):
    _schedule(instance.work_id or (instance.edition.work_id if instance.edition_id else None))


@receiver([post_save, post_delete], sender=Edition)
def edition_changed(sender, instance, **kwargs):
    _schedule(instance.work_id)
