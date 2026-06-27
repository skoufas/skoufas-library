"""Curation views for author and book deduplication workflows."""

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import TemplateResponseMixin

from books.models import Author, BookEntry, Curator, Editor, EntryNumber, Location, Topic, Translator
from curation.models import InventorySession, InventorySessionEntry, MergeLog, SuppressedPair
from curation.queries import BOOK_BOOLEAN_FIELDS, BOOK_SCALAR_FIELDS, DEFAULT_SIMILARITY_THRESHOLD
from curation.queries import (
    get_duplicate_author_pairs,
    get_duplicate_book_pairs,
    get_duplicate_curator_pairs,
    get_duplicate_editor_pairs,
    get_duplicate_topic_pairs,
    get_duplicate_translator_pairs,
)
from loaning.models import Loan


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
# Translator duplicate detection & merge
# ---------------------------------------------------------------------------


class TranslatorDuplicatesView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """List translator pairs above the similarity threshold."""

    permission_required = "curation.can_curate"
    template_name = "curation/person_duplicates.html"

    def get(self, request):
        threshold = _threshold_from_request(request)
        include_suppressed = request.GET.get("show_suppressed") == "1"
        pairs = get_duplicate_translator_pairs(threshold, include_suppressed=include_suppressed)
        return self.render_to_response(
            {
                "pairs": pairs,
                "threshold": threshold,
                "include_suppressed": include_suppressed,
                "page_title": _("Translator Duplicates"),
                "entity_label": _("Translator"),
                "duplicates_url": "curation:translator-duplicates",
                "merge_review_url_name": "curation:translator-merge-review",
            }
        )


class TranslatorMergeReviewView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Show two translators side-by-side and allow the user to pick the canonical one."""

    permission_required = "curation.can_curate"
    template_name = "curation/person_merge_review.html"

    def _get_with_books(self, a_id, b_id):
        obj_a = get_object_or_404(Translator, pk=a_id)
        obj_b = get_object_or_404(Translator, pk=b_id)
        obj_a.books = BookEntry.objects.filter(translators=obj_a).order_by("title")
        obj_b.books = BookEntry.objects.filter(translators=obj_b).order_by("title")
        return obj_a, obj_b

    def _context(self, obj_a, obj_b):
        return {
            "object_a": obj_a,
            "object_b": obj_b,
            "objects": [obj_a, obj_b],
            "entity_label": _("Translator"),
            "duplicates_url": "curation:translator-duplicates",
        }

    def get(self, request, a_id, b_id):
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        ct = ContentType.objects.get_for_model(Translator)
        action = request.POST.get("action")

        if action == "suppress":
            _suppress_pair(ct, min(a_id, b_id), max(a_id, b_id), request.user)
            messages.success(request, _("Pair dismissed."))
            return redirect("curation:translator-duplicates")

        canonical_id = request.POST.get("canonical")
        if not canonical_id:
            messages.error(request, _("Please select the canonical translator."))
            obj_a, obj_b = self._get_with_books(a_id, b_id)
            return self.render_to_response(self._context(obj_a, obj_b))

        canonical_id = int(canonical_id)
        source_id = b_id if canonical_id == a_id else a_id

        with transaction.atomic():
            target = get_object_or_404(Translator, pk=canonical_id)
            source = get_object_or_404(Translator, pk=source_id)

            target_book_ids = set(target.bookentry_set.values_list("pk", flat=True))
            source_books = list(source.bookentry_set.all())
            repointed_book_ids = [b.pk for b in source_books if b.pk not in target_book_ids]

            target.bookentry_set.add(*source_books)

            SuppressedPair.objects.filter(content_type=ct, object_a_id=source.pk).delete()
            SuppressedPair.objects.filter(content_type=ct, object_b_id=source.pk).delete()

            merge_data = {
                "entity_type": "translator",
                "source_display": str(source),
                "source_fields": {
                    "first_name": source.first_name,
                    "middle_name": source.middle_name,
                    "surname": source.surname,
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

        messages.success(request, _("Translators merged successfully."))
        return redirect("curation:translator-duplicates")


# ---------------------------------------------------------------------------
# Curator duplicate detection & merge
# ---------------------------------------------------------------------------


class CuratorDuplicatesView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """List curator pairs above the similarity threshold."""

    permission_required = "curation.can_curate"
    template_name = "curation/person_duplicates.html"

    def get(self, request):
        threshold = _threshold_from_request(request)
        include_suppressed = request.GET.get("show_suppressed") == "1"
        pairs = get_duplicate_curator_pairs(threshold, include_suppressed=include_suppressed)
        return self.render_to_response(
            {
                "pairs": pairs,
                "threshold": threshold,
                "include_suppressed": include_suppressed,
                "page_title": _("Curator Duplicates"),
                "entity_label": _("Curator"),
                "duplicates_url": "curation:curator-duplicates",
                "merge_review_url_name": "curation:curator-merge-review",
            }
        )


class CuratorMergeReviewView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Show two curators side-by-side and allow the user to pick the canonical one."""

    permission_required = "curation.can_curate"
    template_name = "curation/person_merge_review.html"

    def _get_with_books(self, a_id, b_id):
        obj_a = get_object_or_404(Curator, pk=a_id)
        obj_b = get_object_or_404(Curator, pk=b_id)
        obj_a.books = BookEntry.objects.filter(curators=obj_a).order_by("title")
        obj_b.books = BookEntry.objects.filter(curators=obj_b).order_by("title")
        return obj_a, obj_b

    def _context(self, obj_a, obj_b):
        return {
            "object_a": obj_a,
            "object_b": obj_b,
            "objects": [obj_a, obj_b],
            "entity_label": _("Curator"),
            "duplicates_url": "curation:curator-duplicates",
        }

    def get(self, request, a_id, b_id):
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        ct = ContentType.objects.get_for_model(Curator)
        action = request.POST.get("action")

        if action == "suppress":
            _suppress_pair(ct, min(a_id, b_id), max(a_id, b_id), request.user)
            messages.success(request, _("Pair dismissed."))
            return redirect("curation:curator-duplicates")

        canonical_id = request.POST.get("canonical")
        if not canonical_id:
            messages.error(request, _("Please select the canonical curator."))
            obj_a, obj_b = self._get_with_books(a_id, b_id)
            return self.render_to_response(self._context(obj_a, obj_b))

        canonical_id = int(canonical_id)
        source_id = b_id if canonical_id == a_id else a_id

        with transaction.atomic():
            target = get_object_or_404(Curator, pk=canonical_id)
            source = get_object_or_404(Curator, pk=source_id)

            target_book_ids = set(target.bookentry_set.values_list("pk", flat=True))
            source_books = list(source.bookentry_set.all())
            repointed_book_ids = [b.pk for b in source_books if b.pk not in target_book_ids]

            target.bookentry_set.add(*source_books)

            SuppressedPair.objects.filter(content_type=ct, object_a_id=source.pk).delete()
            SuppressedPair.objects.filter(content_type=ct, object_b_id=source.pk).delete()

            merge_data = {
                "entity_type": "curator",
                "source_display": str(source),
                "source_fields": {
                    "first_name": source.first_name,
                    "middle_name": source.middle_name,
                    "surname": source.surname,
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

        messages.success(request, _("Curators merged successfully."))
        return redirect("curation:curator-duplicates")


# ---------------------------------------------------------------------------
# Topic duplicate detection & merge
# ---------------------------------------------------------------------------


class TopicDuplicatesView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """List topic pairs above the similarity threshold."""

    permission_required = "curation.can_curate"
    template_name = "curation/person_duplicates.html"

    def get(self, request):
        threshold = _threshold_from_request(request)
        include_suppressed = request.GET.get("show_suppressed") == "1"
        pairs = get_duplicate_topic_pairs(threshold, include_suppressed=include_suppressed)
        return self.render_to_response(
            {
                "pairs": pairs,
                "threshold": threshold,
                "include_suppressed": include_suppressed,
                "page_title": _("Topic Duplicates"),
                "entity_label": _("Topic"),
                "duplicates_url": "curation:topic-duplicates",
                "merge_review_url_name": "curation:topic-merge-review",
            }
        )


class TopicMergeReviewView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Show two topics side-by-side and allow the user to pick the canonical one."""

    permission_required = "curation.can_curate"
    template_name = "curation/topic_merge_review.html"

    def _get_with_books(self, a_id, b_id):
        obj_a = get_object_or_404(Topic, pk=a_id)
        obj_b = get_object_or_404(Topic, pk=b_id)
        obj_a.books = BookEntry.objects.filter(topics=obj_a).order_by("title")
        obj_b.books = BookEntry.objects.filter(topics=obj_b).order_by("title")
        return obj_a, obj_b

    def _context(self, obj_a, obj_b):
        return {
            "object_a": obj_a,
            "object_b": obj_b,
            "objects": [obj_a, obj_b],
        }

    def get(self, request, a_id, b_id):
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        ct = ContentType.objects.get_for_model(Topic)
        action = request.POST.get("action")

        if action == "suppress":
            _suppress_pair(ct, min(a_id, b_id), max(a_id, b_id), request.user)
            messages.success(request, _("Pair dismissed."))
            return redirect("curation:topic-duplicates")

        canonical_id = request.POST.get("canonical")
        if not canonical_id:
            messages.error(request, _("Please select the canonical topic."))
            obj_a, obj_b = self._get_with_books(a_id, b_id)
            return self.render_to_response(self._context(obj_a, obj_b))

        canonical_id = int(canonical_id)
        source_id = b_id if canonical_id == a_id else a_id

        with transaction.atomic():
            target = get_object_or_404(Topic, pk=canonical_id)
            source = get_object_or_404(Topic, pk=source_id)

            target_book_ids = set(target.bookentry_set.values_list("pk", flat=True))
            source_books = list(source.bookentry_set.all())
            repointed_book_ids = [b.pk for b in source_books if b.pk not in target_book_ids]

            target.bookentry_set.add(*source_books)

            SuppressedPair.objects.filter(content_type=ct, object_a_id=source.pk).delete()
            SuppressedPair.objects.filter(content_type=ct, object_b_id=source.pk).delete()

            merge_data = {
                "entity_type": "topic",
                "source_display": str(source),
                "source_fields": {
                    "topic_name": source.topic_name,
                    "romanized_topic_name": source.romanized_topic_name,
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

        messages.success(request, _("Topics merged successfully."))
        return redirect("curation:topic-duplicates")


# ---------------------------------------------------------------------------
# Editor duplicate detection & merge
# ---------------------------------------------------------------------------


class EditorDuplicatesView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """List editor pairs above the similarity threshold."""

    permission_required = "curation.can_curate"
    template_name = "curation/person_duplicates.html"

    def get(self, request):
        threshold = _threshold_from_request(request)
        include_suppressed = request.GET.get("show_suppressed") == "1"
        pairs = get_duplicate_editor_pairs(threshold, include_suppressed=include_suppressed)
        return self.render_to_response(
            {
                "pairs": pairs,
                "threshold": threshold,
                "include_suppressed": include_suppressed,
                "page_title": _("Editor Duplicates"),
                "entity_label": _("Editor"),
                "duplicates_url": "curation:editor-duplicates",
                "merge_review_url_name": "curation:editor-merge-review",
            }
        )


class EditorMergeReviewView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Show two editors side-by-side and allow the user to pick the canonical one."""

    permission_required = "curation.can_curate"
    template_name = "curation/editor_merge_review.html"

    def _get_with_books(self, a_id, b_id):
        obj_a = get_object_or_404(Editor, pk=a_id)
        obj_b = get_object_or_404(Editor, pk=b_id)
        obj_a.books = BookEntry.objects.filter(editor=obj_a).order_by("title")
        obj_b.books = BookEntry.objects.filter(editor=obj_b).order_by("title")
        return obj_a, obj_b

    def _context(self, obj_a, obj_b):
        return {
            "object_a": obj_a,
            "object_b": obj_b,
            "objects": [obj_a, obj_b],
        }

    def get(self, request, a_id, b_id):
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        ct = ContentType.objects.get_for_model(Editor)
        action = request.POST.get("action")

        if action == "suppress":
            _suppress_pair(ct, min(a_id, b_id), max(a_id, b_id), request.user)
            messages.success(request, _("Pair dismissed."))
            return redirect("curation:editor-duplicates")

        canonical_id = request.POST.get("canonical")
        if not canonical_id:
            messages.error(request, _("Please select the canonical editor."))
            obj_a, obj_b = self._get_with_books(a_id, b_id)
            return self.render_to_response(self._context(obj_a, obj_b))

        canonical_id = int(canonical_id)
        source_id = b_id if canonical_id == a_id else a_id

        with transaction.atomic():
            target = get_object_or_404(Editor, pk=canonical_id)
            source = get_object_or_404(Editor, pk=source_id)

            repointed_book_ids = list(source.bookentry_set.values_list("pk", flat=True))
            source.bookentry_set.update(editor=target)

            SuppressedPair.objects.filter(content_type=ct, object_a_id=source.pk).delete()
            SuppressedPair.objects.filter(content_type=ct, object_b_id=source.pk).delete()

            merge_data = {
                "entity_type": "editor",
                "source_display": str(source),
                "source_fields": {
                    "name": source.name,
                    "place": source.place,
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

        messages.success(request, _("Editors merged successfully."))
        return redirect("curation:editor-duplicates")


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


class MergeUndoView(PermissionRequiredMixin, View):
    """Generic undo view: dispatches by entity_type stored in merge_data."""

    permission_required = "curation.can_curate"

    def post(self, request, log_id):
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
        if entity_type == "translator":
            return redirect("curation:translator-duplicates")
        if entity_type == "curator":
            return redirect("curation:curator-duplicates")
        if entity_type == "topic":
            return redirect("curation:topic-duplicates")
        if entity_type == "editor":
            return redirect("curation:editor-duplicates")
        return redirect("curation:author-duplicates")


# ---------------------------------------------------------------------------
# Inventory workflow
# ---------------------------------------------------------------------------

_LEAF_TYPES = {Location.TYPE_SHELF, Location.TYPE_BOX}
_PENDING_KEY = "inventory_pending_entry_number_id"
_PENDING_CONFLICT = "inventory_pending_conflict"


class InventorySessionListView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Hub: list open sessions and allow starting a new one."""

    permission_required = "curation.can_inventory"
    template_name = "curation/inventory_session_list.html"

    def get(self, request):
        open_sessions = InventorySession.objects.filter(closed_at=None).select_related("location", "started_by")
        recent_closed = InventorySession.objects.exclude(closed_at=None).select_related("location", "started_by")[:10]
        leaf_locations = Location.objects.filter(type__in=_LEAF_TYPES).order_by("name")
        return self.render_to_response(
            {"open_sessions": open_sessions, "recent_closed": recent_closed, "leaf_locations": leaf_locations}
        )

    def post(self, request):
        location_id = request.POST.get("location_id")
        location = get_object_or_404(Location, pk=location_id)
        if location.type not in _LEAF_TYPES:
            messages.error(request, _("Only Shelf or Box locations can be inventoried."))
            return redirect("curation:inventory-list")
        try:
            session = InventorySession.objects.create(location=location, started_by=request.user)
        except IntegrityError:
            existing = InventorySession.objects.get(location=location, closed_at=None)
            messages.error(
                request,
                _("An open inventory session already exists for this location."),
            )
            return redirect("curation:inventory-scan", pk=existing.pk)
        return redirect("curation:inventory-scan", pk=session.pk)


class InventorySessionScanView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Scan screen: show scan input and handle pending confirmation."""

    permission_required = "curation.can_inventory"
    template_name = "curation/inventory_scan.html"

    def _session(self, pk):
        return get_object_or_404(InventorySession, pk=pk, closed_at=None)

    def _pending_context(self, request, session):
        """Return context dict for the pending entry review, or empty dict."""
        en_id = request.session.get(_PENDING_KEY)
        if not en_id:
            return {}
        try:
            en = EntryNumber.objects.select_related("book_entry", "location").get(pk=en_id)
        except EntryNumber.DoesNotExist:
            request.session.pop(_PENDING_KEY, None)
            request.session.pop(_PENDING_CONFLICT, None)
            return {}
        return {
            "pending": en,
            "pending_conflict": request.session.get(_PENDING_CONFLICT, False),
        }

    def get(self, request, pk):
        session = self._session(pk)
        recent = session.entries.select_related("entry_number__book_entry").order_by("-scanned_at")[:10]
        ctx = {"session": session, "recent_entries": recent}
        ctx.update(self._pending_context(request, session))
        return self.render_to_response(ctx)

    def post(self, request, pk):
        session = self._session(pk)
        entry_number_value = request.POST.get("entry_number", "").strip()
        if not entry_number_value:
            messages.error(request, _("Please enter an entry number."))
            return redirect("curation:inventory-scan", pk=pk)

        try:
            en = (
                EntryNumber.objects.select_related("book_entry", "location")
                .prefetch_related("book_entry__authors")
                .get(entry_number=entry_number_value)
            )
        except EntryNumber.DoesNotExist:
            messages.error(request, _('Entry number "%(en)s" not found in the database.') % {"en": entry_number_value})
            return redirect("curation:inventory-scan", pk=pk)

        conflict = en.location_id is not None and en.location_id != session.location_id
        request.session[_PENDING_KEY] = en.pk
        request.session[_PENDING_CONFLICT] = conflict
        return redirect("curation:inventory-scan", pk=pk)


class InventorySessionConfirmView(PermissionRequiredMixin, View):
    """Confirm scanned entry: assign location and record the session entry."""

    permission_required = "curation.can_inventory"

    def post(self, request, pk):
        session = get_object_or_404(InventorySession, pk=pk, closed_at=None)
        en_id = request.session.get(_PENDING_KEY)
        if not en_id:
            messages.error(request, _("No pending scan to confirm."))
            return redirect("curation:inventory-scan", pk=pk)

        en = get_object_or_404(EntryNumber, pk=en_id)
        with transaction.atomic():
            previous_location = en.location
            en.location = session.location
            en.save(update_fields=["location"])
            InventorySessionEntry.objects.create(
                session=session,
                entry_number=en,
                outcome=InventorySessionEntry.OUTCOME_CONFIRMED,
                previous_location=previous_location if previous_location != session.location else None,
            )

        request.session.pop(_PENDING_KEY, None)
        request.session.pop(_PENDING_CONFLICT, None)
        messages.success(
            request,
            _("%(en)s confirmed and assigned to %(loc)s.") % {"en": en.entry_number, "loc": session.location},
        )
        return redirect("curation:inventory-scan", pk=pk)


class InventorySessionSetAsideView(PermissionRequiredMixin, View):
    """Set aside a scanned entry: flag it without changing its location."""

    permission_required = "curation.can_inventory"

    def post(self, request, pk):
        session = get_object_or_404(InventorySession, pk=pk, closed_at=None)
        en_id = request.session.get(_PENDING_KEY)
        if not en_id:
            messages.error(request, _("No pending scan to set aside."))
            return redirect("curation:inventory-scan", pk=pk)

        en = get_object_or_404(EntryNumber, pk=en_id)
        InventorySessionEntry.objects.create(
            session=session,
            entry_number=en,
            outcome=InventorySessionEntry.OUTCOME_SET_ASIDE,
            previous_location=en.location,
        )
        request.session.pop(_PENDING_KEY, None)
        request.session.pop(_PENDING_CONFLICT, None)
        messages.warning(
            request,
            _("%(en)s set aside for entry number reassignment.") % {"en": en.entry_number},
        )
        return redirect("curation:inventory-scan", pk=pk)


class InventorySessionCloseView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Reconciliation report + close the session."""

    permission_required = "curation.can_inventory"
    template_name = "curation/inventory_close.html"

    def _reconciliation(self, session):
        scanned_ids = set(session.entries.values_list("entry_number_id", flat=True))
        expected = EntryNumber.objects.filter(location=session.location).select_related("book_entry")
        expected_ids = set(expected.values_list("pk", flat=True))
        missing_ids = expected_ids - scanned_ids

        confirmed = session.entries.filter(outcome=InventorySessionEntry.OUTCOME_CONFIRMED).select_related(
            "entry_number__book_entry", "previous_location"
        )
        set_aside = session.entries.filter(outcome=InventorySessionEntry.OUTCOME_SET_ASIDE).select_related(
            "entry_number__book_entry", "previous_location"
        )
        missing = EntryNumber.objects.filter(pk__in=missing_ids).select_related("book_entry")

        return {
            "confirmed": confirmed,
            "set_aside": set_aside,
            "missing": missing,
            "confirmed_count": confirmed.count(),
            "set_aside_count": set_aside.count(),
            "missing_count": len(missing_ids),
        }

    def get(self, request, pk):
        session = get_object_or_404(InventorySession, pk=pk)
        ctx = {"session": session, "read_only": session.closed_at is not None}
        ctx.update(self._reconciliation(session))
        return self.render_to_response(ctx)

    def post(self, request, pk):
        session = get_object_or_404(InventorySession, pk=pk, closed_at=None)
        session.closed_at = timezone.now()
        session.save(update_fields=["closed_at"])
        messages.success(request, _("Inventory session for %(loc)s closed.") % {"loc": session.location})
        return redirect("curation:inventory-list")
