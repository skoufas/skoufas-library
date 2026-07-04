"""Tests for the merge log list and undo (entity-recreation) views."""

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from books.models import Author
from books.models import BookEntry
from books.models import Curator
from books.models import Editor
from books.models import EntryNumber
from books.models import Topic
from books.models import Translator
from curation.models import MergeLog


def _grant_can_curate(user):
    user.user_permissions.add(Permission.objects.get(codename="can_curate"))


class MergeLogListViewTests(TestCase):
    """Tests for the merge history list and its custom pagination clamping."""

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the merge log."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:merge-log-list"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_merge_logs(self):
        """The merge log lists past merges by source display name."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "author", "source_display": "Deleted Source Author"},
            merged_by=self.user,
        )

        response = self.client.get(reverse("curation:merge-log-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deleted Source Author")

    def test_list_invalid_page_defaults_to_first_page(self):
        """A non-numeric page parameter falls back to page 1 instead of erroring."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "author", "source_display": "Some Source"},
            merged_by=self.user,
        )

        response = self.client.get(reverse("curation:merge-log-list"), {"page": "not-a-number"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Some Source")
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_list_out_of_range_page_defaults_to_last_page(self):
        """A page number beyond the last page falls back to the last page instead of 404ing."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "author", "source_display": "Some Source"},
            merged_by=self.user,
        )

        response = self.client.get(reverse("curation:merge-log-list"), {"page": "9999"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)


class MergeUndoViewTests(TestCase):
    """Tests for undoing a merge, recreating the deleted source entity for each entity type."""

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_undo_denies_without_permission(self):
        """A user lacking can_curate is denied access to undo a merge."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "author", "source_display": "Source Author"},
            merged_by=self.user,
        )
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertEqual(response.status_code, 403)

    def test_undo_already_undone_shows_error(self):
        """Undoing an already-undone merge is rejected with an error message."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "author", "source_display": "Source Author"},
            merged_by=self.user,
            undone_at=timezone.now(),
            undone_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("This merge has already been undone.", messages)
        self.assertFalse(Author.objects.filter(surname="Source Author").exists())

    def test_undo_when_target_deleted_shows_error(self):
        """Undoing a merge whose target no longer exists is rejected with an error message."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "author", "source_display": "Source Author"},
            merged_by=self.user,
        )
        target.delete()

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Cannot undo: the target object no longer exists.", messages)

    def test_undo_unknown_entity_type_shows_error(self):
        """Undoing a merge log with an unrecognized entity_type is rejected."""
        target = Author.objects.create(surname="Target Author")
        ct = ContentType.objects.get_for_model(Author)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={"entity_type": "widget", "source_display": "Source Widget"},
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Unknown entity type - cannot undo.", messages)
        log.refresh_from_db()
        self.assertFalse(log.is_undone)

    def test_undo_author_recreates_source_and_moves_books_back(self):
        """Undoing an author merge recreates the source author and moves its books off the target."""
        target = Author.objects.create(surname="Target Author")
        book = BookEntry.objects.create(title="Shared Book", offprint=False, has_cd=False, has_dvd=False)
        book.authors.add(target)
        ct = ContentType.objects.get_for_model(Author)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={
                "entity_type": "author",
                "source_display": "Source Author",
                "source_fields": {
                    "first_name": None,
                    "middle_name": None,
                    "surname": "Source Author",
                    "pseudonym": None,
                    "organisation_name": None,
                    "romanized_name": "source author",
                },
                "repointed_book_ids": [book.pk],
            },
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        recreated = Author.objects.get(surname="Source Author")
        self.assertIn(recreated, book.authors.all())
        self.assertNotIn(target, book.authors.all())
        log.refresh_from_db()
        self.assertTrue(log.is_undone)
        self.assertEqual(log.undone_by, self.user)

    def test_undo_translator_recreates_source_and_moves_books_back(self):
        """Undoing a translator merge recreates the source translator and moves its books off the target."""
        target = Translator.objects.create(first_name="Target", surname="Translator")
        book = BookEntry.objects.create(title="Shared Book", offprint=False, has_cd=False, has_dvd=False)
        book.translators.add(target)
        ct = ContentType.objects.get_for_model(Translator)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={
                "entity_type": "translator",
                "source_display": "Source Translator",
                "source_fields": {
                    "first_name": "Source",
                    "middle_name": None,
                    "surname": "Translator",
                    "organisation_name": None,
                    "romanized_name": "source translator",
                },
                "repointed_book_ids": [book.pk],
            },
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        recreated = Translator.objects.get(first_name="Source", surname="Translator")
        self.assertIn(recreated, book.translators.all())
        self.assertNotIn(target, book.translators.all())
        log.refresh_from_db()
        self.assertTrue(log.is_undone)

    def test_undo_curator_recreates_source_and_moves_books_back(self):
        """Undoing a curator merge recreates the source curator and moves its books off the target."""
        target = Curator.objects.create(first_name="Target", surname="Curator")
        book = BookEntry.objects.create(title="Shared Book", offprint=False, has_cd=False, has_dvd=False)
        book.curators.add(target)
        ct = ContentType.objects.get_for_model(Curator)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={
                "entity_type": "curator",
                "source_display": "Source Curator",
                "source_fields": {
                    "first_name": "Source",
                    "middle_name": None,
                    "surname": "Curator",
                    "organisation_name": None,
                    "romanized_name": "source curator",
                },
                "repointed_book_ids": [book.pk],
            },
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        recreated = Curator.objects.get(first_name="Source", surname="Curator")
        self.assertIn(recreated, book.curators.all())
        self.assertNotIn(target, book.curators.all())
        log.refresh_from_db()
        self.assertTrue(log.is_undone)

    def test_undo_topic_recreates_source_and_moves_books_back(self):
        """Undoing a topic merge recreates the source topic and moves its books off the target."""
        target = Topic.objects.create(topic_name="Target Topic")
        book = BookEntry.objects.create(title="Shared Book", offprint=False, has_cd=False, has_dvd=False)
        book.topics.add(target)
        ct = ContentType.objects.get_for_model(Topic)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={
                "entity_type": "topic",
                "source_display": "Source Topic",
                "source_fields": {"topic_name": "Source Topic", "romanized_topic_name": "source topic"},
                "repointed_book_ids": [book.pk],
            },
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        recreated = Topic.objects.get(topic_name="Source Topic")
        self.assertIn(recreated, book.topics.all())
        self.assertNotIn(target, book.topics.all())
        log.refresh_from_db()
        self.assertTrue(log.is_undone)

    def test_undo_editor_recreates_source_and_repoints_books_by_fk(self):
        """Undoing an editor merge recreates the source editor and re-points its books via the FK."""
        target = Editor.objects.create(name="Target Editor")
        book = BookEntry.objects.create(title="Shared Book", offprint=False, has_cd=False, has_dvd=False, editor=target)
        ct = ContentType.objects.get_for_model(Editor)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={
                "entity_type": "editor",
                "source_display": "Source Editor",
                "source_fields": {"name": "Source Editor", "place": None, "romanized_name": "source editor"},
                "repointed_book_ids": [book.pk],
            },
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        recreated = Editor.objects.get(name="Source Editor")
        book.refresh_from_db()
        self.assertEqual(book.editor_id, recreated.pk)
        log.refresh_from_db()
        self.assertTrue(log.is_undone)

    def test_undo_book_reverts_target_and_recreates_source_with_its_relations(self):
        """Undoing a book merge reverts the target's overwritten fields and recreates the source entry."""
        author_shared = Author.objects.create(surname="Shared Author")
        target = BookEntry.objects.create(
            title="Zorba the Greek",
            subtitle="An epic novel",
            offprint=False,
            has_cd=True,
            has_dvd=False,
            pages=350,
        )
        target.authors.add(author_shared)
        entry_number = EntryNumber.objects.create(entry_number=1002, book_entry=target, copies=1)
        ct = ContentType.objects.get_for_model(BookEntry)
        log = MergeLog.objects.create(
            content_type=ct,
            target_object_id=target.pk,
            merge_data={
                "entity_type": "book",
                "source_display": "Zorba the Greek - An epic novel",
                "source_fields": {
                    "title": "Zorba the Greek",
                    "subtitle": "An epic novel",
                    "skoufas_classification": None,
                    "language": None,
                    "edition": None,
                    "edition_year": None,
                    "pages": 350,
                    "copies": None,
                    "volumes": None,
                    "notes": None,
                    "material": None,
                    "isbn": None,
                    "issn": None,
                    "ean": None,
                    "editor_id": None,
                    "offprint": False,
                    "has_cd": True,
                    "has_dvd": False,
                },
                "source_m2m": {
                    "authors": [author_shared.pk],
                    "translators": [],
                    "curators": [],
                    "topics": [],
                    "entry_donors": [],
                },
                "target_fields_before": {"subtitle": "A novel", "pages": 300},
                "added_m2m_to_target": {"authors": [author_shared.pk]},
                "repointed_entry_number_ids": [entry_number.pk],
            },
            merged_by=self.user,
        )

        response = self.client.post(reverse("curation:merge-undo", kwargs={"log_id": log.pk}))

        self.assertRedirects(response, reverse("curation:merge-log-list"))
        target.refresh_from_db()
        self.assertEqual(target.subtitle, "A novel")
        self.assertEqual(target.pages, 300)
        self.assertNotIn(author_shared, target.authors.all())

        recreated = BookEntry.objects.get(subtitle="An epic novel")
        self.assertEqual(recreated.pages, 350)
        self.assertTrue(recreated.has_cd)
        self.assertIn(author_shared, recreated.authors.all())
        entry_number.refresh_from_db()
        self.assertEqual(entry_number.book_entry_id, recreated.pk)

        log.refresh_from_db()
        self.assertTrue(log.is_undone)
