"""Merge log listing and undo views."""

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView

from books.models import Author, BookEntry, Curator, Editor, EntryNumber, Topic, Translator
from curation.models import MergeLog
from curation.queries import BOOK_BOOLEAN_FIELDS, BOOK_SCALAR_FIELDS


class MergeLogListView(PermissionRequiredMixin, ListView):
    """List all merge operations with undo buttons."""

    permission_required = "curation.can_curate"
    model = MergeLog
    template_name = "curation/merge_log_list.html"
    paginate_by = 50
    context_object_name = "merge_logs"

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size)
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError, TypeError:
            page_number = 1
        try:
            page = paginator.page(page_number)
        except Exception:
            page = paginator.page(paginator.num_pages or 1)
        return paginator, page, page.object_list, page.has_other_pages()


class MergeUndoView(PermissionRequiredMixin, View):
    """Generic undo view: dispatches by entity_type stored in merge_data."""

    permission_required = "curation.can_curate"

    def post(self, request, log_id):
        """Undo the given merge, recreating the deleted source object."""
        log = get_object_or_404(MergeLog, pk=log_id)
        if log.is_undone:
            messages.error(request, _("This merge has already been undone."))
            return redirect("curation:merge-log-list")
        if not log.can_undo:
            messages.error(request, _("Cannot undo: the target object no longer exists."))
            return redirect("curation:merge-log-list")

        entity_type = log.merge_data.get("entity_type")
        if entity_type == "book":
            recreated = self._undo_book(log, request.user)
        elif entity_type == "author":
            recreated = self._undo_person(log, Author, "bookentry_set", request.user)
        elif entity_type == "translator":
            recreated = self._undo_person(log, Translator, "bookentry_set", request.user)
        elif entity_type == "curator":
            recreated = self._undo_person(log, Curator, "bookentry_set", request.user)
        elif entity_type == "topic":
            recreated = self._undo_person(log, Topic, "bookentry_set", request.user)
        elif entity_type == "editor":
            recreated = self._undo_fk_entity(log, Editor, "editor", request.user)
        else:
            messages.error(request, _("Unknown entity type — cannot undo."))
            return redirect("curation:merge-log-list")

        messages.success(request, _('Merge undone. Entry recreated as "%(name)s".') % {"name": str(recreated)})
        return redirect("curation:merge-log-list")

    def _undo_person(self, log, model_class, books_attr, user):
        with transaction.atomic():
            data = log.merge_data
            target = log.target_object
            recreated = model_class.objects.create(**data["source_fields"])
            if data.get("repointed_book_ids"):
                books = BookEntry.objects.filter(pk__in=data["repointed_book_ids"])
                getattr(recreated, books_attr).add(*books)
                getattr(target, books_attr).remove(*books)
            log.undone_at = timezone.now()
            log.undone_by = user
            log.save(update_fields=["undone_at", "undone_by"])
        return recreated

    def _undo_fk_entity(self, log, model_class, fk_field, user):
        with transaction.atomic():
            data = log.merge_data
            recreated = model_class.objects.create(**data["source_fields"])
            if data.get("repointed_book_ids"):
                BookEntry.objects.filter(pk__in=data["repointed_book_ids"]).update(**{fk_field: recreated})
            log.undone_at = timezone.now()
            log.undone_by = user
            log.save(update_fields=["undone_at", "undone_by"])
        return recreated

    def _undo_book(self, log, user):
        with transaction.atomic():
            data = log.merge_data
            target = log.target_object

            for field, old_val in data.get("target_fields_before", {}).items():
                setattr(target, field, old_val)
            target.save()

            for attr, ids in data.get("added_m2m_to_target", {}).items():
                if ids:
                    getattr(target, attr).remove(*ids)

            source_fields = {
                k: v for k, v in data["source_fields"].items() if k in BOOK_SCALAR_FIELDS + BOOK_BOOLEAN_FIELDS
            }
            recreated = BookEntry.objects.create(**source_fields)

            for attr, ids in data.get("source_m2m", {}).items():
                if ids:
                    getattr(recreated, attr).add(*ids)

            if data.get("repointed_entry_number_ids"):
                EntryNumber.objects.filter(pk__in=data["repointed_entry_number_ids"]).update(book_entry=recreated)

            log.undone_at = timezone.now()
            log.undone_by = user
            log.save(update_fields=["undone_at", "undone_by"])
        return recreated
