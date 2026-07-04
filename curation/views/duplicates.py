"""Duplicate detection & merge views for authors, books, translators, curators, topics, editors."""

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import TemplateResponseMixin

from books.models import Author, BookEntry, Curator, Editor, Topic, Translator
from curation.models import MergeLog, SuppressedPair
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
        """List author pairs above the requested similarity threshold."""
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
        """Show the two candidate authors side-by-side for review."""
        author_a, author_b = self._get_authors_with_books(a_id, b_id)
        return self.render_to_response({"author_a": author_a, "author_b": author_b, "authors": [author_a, author_b]})

    def post(self, request, a_id, b_id):
        """Dismiss the pair or merge them into the selected canonical author."""
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
        """List book entry pairs above the requested similarity threshold."""
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
        """Show the two candidate book entries side-by-side with conflict resolution."""
        book_a, book_b = self._load(a_id, b_id)
        return self.render_to_response(self._context(book_a, book_b))

    # Field-by-field conflict resolution across scalar/boolean/M2M attributes,
    # plus undo-log snapshotting - inherently touches many local values.
    # pylint: disable-next=too-many-locals
    def post(self, request, a_id, b_id):
        """Dismiss the pair or merge them, applying the user's per-field choices."""
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
        """List translator pairs above the requested similarity threshold."""
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
        """Show the two candidate translators side-by-side for review."""
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        """Dismiss the pair or merge them into the selected canonical translator."""
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
        """List curator pairs above the requested similarity threshold."""
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
        """Show the two candidate curators side-by-side for review."""
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        """Dismiss the pair or merge them into the selected canonical curator."""
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
        """List topic pairs above the requested similarity threshold."""
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
        """Show the two candidate topics side-by-side for review."""
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        """Dismiss the pair or merge them into the selected canonical topic."""
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
        """List editor pairs above the requested similarity threshold."""
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
        """Show the two candidate editors side-by-side for review."""
        obj_a, obj_b = self._get_with_books(a_id, b_id)
        return self.render_to_response(self._context(obj_a, obj_b))

    def post(self, request, a_id, b_id):
        """Dismiss the pair or merge them into the selected canonical editor."""
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
