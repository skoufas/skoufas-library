"""Curation views for author and book deduplication workflows."""

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import TemplateResponseMixin

from books.models import Author
from books.models import BookEntry
from curation.models import MergeLog
from curation.models import SuppressedPair
from curation.queries import BOOK_BOOLEAN_FIELDS, BOOK_SCALAR_FIELDS, DEFAULT_SIMILARITY_THRESHOLD
from curation.queries import get_duplicate_author_pairs, get_duplicate_book_pairs


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _suppress_pair(content_type, lo_id, hi_id, user):
    SuppressedPair.objects.get_or_create(
        content_type=content_type,
        object_a_id=lo_id,
        object_b_id=hi_id,
        defaults={"suppressed_by": user},
    )


def _threshold_from_request(request):
    try:
        threshold = float(request.GET.get("threshold", DEFAULT_SIMILARITY_THRESHOLD))
        return max(0.1, min(1.0, threshold))
    except ValueError, TypeError:
        return DEFAULT_SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# Author duplicate detection & merge
# ---------------------------------------------------------------------------


class AuthorDuplicatesView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """List author pairs above the similarity threshold."""

    permission_required = "curation.can_curate"
    template_name = "curation/author_duplicates.html"

    def get(self, request):
        threshold = _threshold_from_request(request)
        include_suppressed = request.GET.get("show_suppressed") == "1"
        pairs = get_duplicate_author_pairs(threshold, include_suppressed=include_suppressed)
        return self.render_to_response(
            {"pairs": pairs, "threshold": threshold, "include_suppressed": include_suppressed}
        )


class AuthorMergeReviewView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Show two authors side-by-side and allow the user to pick the canonical one."""

    permission_required = "curation.can_curate"
    template_name = "curation/author_merge_review.html"

    def _get_authors_with_books(self, a_id, b_id):
        author_a = get_object_or_404(Author, pk=a_id)
        author_b = get_object_or_404(Author, pk=b_id)
        author_a.books = BookEntry.objects.filter(authors=author_a).order_by("title")
        author_b.books = BookEntry.objects.filter(authors=author_b).order_by("title")
        return author_a, author_b

    def get(self, request, a_id, b_id):
        author_a, author_b = self._get_authors_with_books(a_id, b_id)
        return self.render_to_response({"author_a": author_a, "author_b": author_b, "authors": [author_a, author_b]})

    def post(self, request, a_id, b_id):
        ct = ContentType.objects.get_for_model(Author)
        action = request.POST.get("action")

        if action == "suppress":
            _suppress_pair(ct, min(a_id, b_id), max(a_id, b_id), request.user)
            messages.success(request, _("Pair dismissed."))
            return redirect("curation:author-duplicates")

        canonical_id = request.POST.get("canonical")
        if not canonical_id:
            messages.error(request, _("Please select the canonical author."))
            author_a, author_b = self._get_authors_with_books(a_id, b_id)
            return self.render_to_response(
                {"author_a": author_a, "author_b": author_b, "authors": [author_a, author_b]}
            )

        canonical_id = int(canonical_id)
        source_id = b_id if canonical_id == a_id else a_id

        with transaction.atomic():
            target = get_object_or_404(Author, pk=canonical_id)
            source = get_object_or_404(Author, pk=source_id)

            target_book_ids = set(target.bookentry_set.values_list("pk", flat=True))
            source_books = list(source.bookentry_set.all())
            repointed_book_ids = [b.pk for b in source_books if b.pk not in target_book_ids]

            target.bookentry_set.add(*source_books)

            SuppressedPair.objects.filter(content_type=ct, object_a_id=source.pk).delete()
            SuppressedPair.objects.filter(content_type=ct, object_b_id=source.pk).delete()

            merge_data = {
                "entity_type": "author",
                "source_display": str(source),
                "source_fields": {
                    "first_name": source.first_name,
                    "middle_name": source.middle_name,
                    "surname": source.surname,
                    "pseudonym": source.pseudonym,
                    "organisation_name": source.organisation_name,
                    "romanized_name": source.romanized_name,
                },
                "repointed_book_ids": repointed_book_ids,
            }

            source.delete()

            MergeLog.objects.create(
                content_type=ct,
                target_object_id=target.pk,
                merge_data=merge_data,
                merged_by=request.user,
            )

        messages.success(request, _("Authors merged successfully."))
        return redirect("curation:author-duplicates")


# ---------------------------------------------------------------------------
# Book duplicate detection & merge
# ---------------------------------------------------------------------------


class BookDuplicatesView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """List book entry pairs above the similarity threshold."""

    permission_required = "curation.can_curate"
    template_name = "curation/book_duplicates.html"

    def get(self, request):
        threshold = _threshold_from_request(request)
        include_suppressed = request.GET.get("show_suppressed") == "1"
        pairs = get_duplicate_book_pairs(threshold, include_suppressed=include_suppressed)
        return self.render_to_response(
            {"pairs": pairs, "threshold": threshold, "include_suppressed": include_suppressed}
        )


def _book_conflicting_fields(book_a, book_b):
    """Return list of dicts for scalar fields that differ between the two books."""
    conflicts = []
    for field in BOOK_SCALAR_FIELDS:
        val_a = getattr(book_a, field)
        val_b = getattr(book_b, field)
        if val_a != val_b:
            default = "b" if (val_a is None or val_a == "") and val_b is not None else "a"
            conflicts.append({"field": field, "value_a": val_a, "value_b": val_b, "default": default})
    return conflicts


def _active_loan_count(book):
    from loaning.models import Loan

    return Loan.objects.filter(entry_number__book_entry=book, status=Loan.STATUS_ACTIVE).count()


class BookMergeReviewView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Show two book entries side-by-side with per-field conflict resolution."""

    permission_required = "curation.can_curate"
    template_name = "curation/book_merge_review.html"

    def _load(self, a_id, b_id):
        book_a = get_object_or_404(BookEntry, pk=a_id)
        book_b = get_object_or_404(BookEntry, pk=b_id)
        book_a.entry_numbers = list(book_a.entrynumber_set.all())
        book_b.entry_numbers = list(book_b.entrynumber_set.all())
        return book_a, book_b

    def _context(self, book_a, book_b):
        return {
            "book_a": book_a,
            "book_b": book_b,
            "books": [book_a, book_b],
            "conflicts": _book_conflicting_fields(book_a, book_b),
            "active_loans_a": _active_loan_count(book_a),
            "active_loans_b": _active_loan_count(book_b),
        }

    def get(self, request, a_id, b_id):
        book_a, book_b = self._load(a_id, b_id)
        return self.render_to_response(self._context(book_a, book_b))

    def post(self, request, a_id, b_id):
        ct = ContentType.objects.get_for_model(BookEntry)
        action = request.POST.get("action")

        if action == "suppress":
            _suppress_pair(ct, min(a_id, b_id), max(a_id, b_id), request.user)
            messages.success(request, _("Pair dismissed."))
            return redirect("curation:book-duplicates")

        canonical_id = request.POST.get("canonical")
        if not canonical_id:
            messages.error(request, _("Please select the canonical book entry."))
            book_a, book_b = self._load(a_id, b_id)
            return self.render_to_response(self._context(book_a, book_b))

        canonical_id = int(canonical_id)
        source_id = b_id if canonical_id == a_id else a_id

        with transaction.atomic():
            target = get_object_or_404(BookEntry, pk=canonical_id)
            source = get_object_or_404(BookEntry, pk=source_id)

            def _m2m_ids(book, attr):
                return list(getattr(book, attr).values_list("pk", flat=True))

            source_fields = {f: getattr(source, f) for f in BOOK_SCALAR_FIELDS + BOOK_BOOLEAN_FIELDS}
            source_m2m = {
                attr: _m2m_ids(source, attr)
                for attr in ["authors", "translators", "curators", "topics", "entry_donors"]
            }

            # Apply user-selected scalar overrides
            target_fields_before = {}
            for field in BOOK_SCALAR_FIELDS:
                chosen = request.POST.get(f"field_{field}", "a")
                source_val = getattr(source, field)
                target_val = getattr(target, field)
                winning_val = source_val if chosen == "b" else target_val
                if winning_val != target_val:
                    target_fields_before[field] = target_val
                    setattr(target, field, winning_val)

            # Booleans: True-wins
            for field in BOOK_BOOLEAN_FIELDS:
                old = getattr(target, field)
                new = old or getattr(source, field)
                if new != old:
                    target_fields_before[field] = old
                    setattr(target, field, new)

            target.save()

            # Union M2M, track what was newly added for undo
            added_m2m = {}
            for attr in ["authors", "translators", "curators", "topics", "entry_donors"]:
                existing_ids = set(getattr(target, attr).values_list("pk", flat=True))
                new_ids = [pk for pk in source_m2m[attr] if pk not in existing_ids]
                if new_ids:
                    getattr(target, attr).add(*new_ids)
                    added_m2m[attr] = new_ids

            # Re-point EntryNumbers
            repointed_entry_number_ids = list(source.entrynumber_set.values_list("pk", flat=True))
            source.entrynumber_set.update(book_entry=target)

            SuppressedPair.objects.filter(content_type=ct, object_a_id=source.pk).delete()
            SuppressedPair.objects.filter(content_type=ct, object_b_id=source.pk).delete()

            merge_data = {
                "entity_type": "book",
                "source_display": str(source),
                "source_fields": source_fields,
                "source_m2m": source_m2m,
                "target_fields_before": target_fields_before,
                "added_m2m_to_target": added_m2m,
                "repointed_entry_number_ids": repointed_entry_number_ids,
            }

            source.delete()

            MergeLog.objects.create(
                content_type=ct,
                target_object_id=target.pk,
                merge_data=merge_data,
                merged_by=request.user,
            )

        messages.success(request, _("Book entries merged successfully."))
        return redirect("curation:book-duplicates")


# ---------------------------------------------------------------------------
# Merge log & undo
# ---------------------------------------------------------------------------


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


class AuthorMergeUndoView(PermissionRequiredMixin, View):
    """Undo an author merge: recreate the source author and re-point books back."""

    permission_required = "curation.can_curate"

    def post(self, request, log_id):
        log = get_object_or_404(MergeLog, pk=log_id)
        if log.is_undone:
            messages.error(request, _("This merge has already been undone."))
            return redirect("curation:merge-log-list")
        if not log.can_undo:
            messages.error(request, _("Cannot undo: the target author no longer exists."))
            return redirect("curation:merge-log-list")

        with transaction.atomic():
            data = log.merge_data
            target = log.target_object
            recreated = Author.objects.create(**data["source_fields"])
            if data.get("repointed_book_ids"):
                books = BookEntry.objects.filter(pk__in=data["repointed_book_ids"])
                recreated.bookentry_set.add(*books)
                target.bookentry_set.remove(*books)
            log.undone_at = timezone.now()
            log.undone_by = request.user
            log.save(update_fields=["undone_at", "undone_by"])

        messages.success(request, _('Merge undone. Author recreated as "%(name)s".') % {"name": str(recreated)})
        return redirect("curation:merge-log-list")


class BookMergeUndoView(PermissionRequiredMixin, View):
    """Undo a book merge: recreate source book, restore target fields, re-point entry numbers."""

    permission_required = "curation.can_curate"

    def post(self, request, log_id):
        log = get_object_or_404(MergeLog, pk=log_id)
        if log.is_undone:
            messages.error(request, _("This merge has already been undone."))
            return redirect("curation:merge-log-list")
        if not log.can_undo:
            messages.error(request, _("Cannot undo: the target book entry no longer exists."))
            return redirect("curation:merge-log-list")

        with transaction.atomic():
            data = log.merge_data
            target = log.target_object

            # Restore target scalar fields
            for field, old_val in data.get("target_fields_before", {}).items():
                setattr(target, field, old_val)
            target.save()

            # Remove M2M items added from source
            for attr, ids in data.get("added_m2m_to_target", {}).items():
                if ids:
                    getattr(target, attr).remove(*ids)

            # Recreate source book
            source_fields = {
                k: v for k, v in data["source_fields"].items() if k in BOOK_SCALAR_FIELDS + BOOK_BOOLEAN_FIELDS
            }
            recreated = BookEntry.objects.create(**source_fields)

            for attr, ids in data.get("source_m2m", {}).items():
                if ids:
                    getattr(recreated, attr).add(*ids)

            if data.get("repointed_entry_number_ids"):
                from books.models import EntryNumber

                EntryNumber.objects.filter(pk__in=data["repointed_entry_number_ids"]).update(book_entry=recreated)

            log.undone_at = timezone.now()
            log.undone_by = request.user
            log.save(update_fields=["undone_at", "undone_by"])

        messages.success(request, _('Merge undone. Book recreated as "%(name)s".') % {"name": str(recreated)})
        return redirect("curation:merge-log-list")


# ---------------------------------------------------------------------------
# Suppression management
# ---------------------------------------------------------------------------


class SuppressedPairUnsuppressView(PermissionRequiredMixin, View):
    """Remove a suppression so the pair reappears in the duplicates list."""

    permission_required = "curation.can_curate"

    def post(self, request, pair_id):
        pair = get_object_or_404(SuppressedPair, pk=pair_id)
        entity_type = pair.content_type.model
        pair.delete()
        messages.success(request, _("Dismissal removed. Pair will reappear in the duplicates list."))
        if entity_type == "bookentry":
            return redirect("curation:book-duplicates")
        return redirect("curation:author-duplicates")
