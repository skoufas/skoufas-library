"""Tests for duplicate detection & merge review across all curated entity types."""

import datetime

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from books.models import Author
from books.models import BookEntry
from books.models import Curator
from books.models import Editor
from books.models import EntryNumber
from books.models import Topic
from books.models import Translator
from curation.models import MergeLog
from curation.models import SuppressedPair
from loaning.models import Customer
from loaning.models import Loan


def _grant_can_curate(user):
    user.user_permissions.add(Permission.objects.get(codename="can_curate"))


class AuthorDuplicatesAndMergeTests(TestCase):
    """Tests for author duplicate detection and merge review."""

    @classmethod
    def setUpTestData(cls):
        """Create two near-duplicate authors, one with a book, and an unrelated author."""
        cls.author_a = Author.objects.create(surname="Kazantzakis")
        cls.author_b = Author.objects.create(surname="Kazantzaki")
        cls.unrelated = Author.objects.create(surname="Completely Different")
        cls.book = BookEntry.objects.create(title="Zorba the Greek", offprint=False, has_cd=False, has_dvd=False)
        cls.book.authors.add(cls.author_b)

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the duplicates list."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:author-duplicates"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_pair_above_threshold(self):
        """The duplicates list finds the near-duplicate author pair at a low threshold."""
        response = self.client.get(reverse("curation:author-duplicates"), {"threshold": "0.1"})

        self.assertEqual(response.status_code, 200)
        merge_url = reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk})
        self.assertContains(response, merge_url)

    def test_list_excludes_suppressed_pair_by_default(self):
        """A dismissed pair is hidden from the duplicates list unless requested."""
        ct = ContentType.objects.get_for_model(Author)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.author_a.pk, object_b_id=self.author_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:author-duplicates"), {"threshold": "0.1"})

        merge_url = reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk})
        self.assertNotContains(response, merge_url)

    def test_list_include_suppressed_shows_dismissed_pair(self):
        """The show_suppressed flag brings a dismissed pair back into the list."""
        ct = ContentType.objects.get_for_model(Author)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.author_a.pk, object_b_id=self.author_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:author-duplicates"), {"threshold": "0.1", "show_suppressed": "1"})

        merge_url = reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk})
        self.assertContains(response, merge_url)

    def test_merge_review_get_shows_both_authors(self):
        """The merge review page renders both candidate authors."""
        response = self.client.get(
            reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kazantzakis")
        self.assertContains(response, "Kazantzaki")

    def test_merge_review_post_suppress_dismisses_pair(self):
        """Dismissing a pair creates a SuppressedPair and leaves both authors intact."""
        response = self.client.post(
            reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk}),
            {"action": "suppress"},
        )

        self.assertRedirects(response, reverse("curation:author-duplicates"))
        ct = ContentType.objects.get_for_model(Author)
        self.assertTrue(
            SuppressedPair.objects.filter(
                content_type=ct, object_a_id=self.author_a.pk, object_b_id=self.author_b.pk
            ).exists()
        )
        self.assertTrue(Author.objects.filter(pk=self.author_b.pk).exists())

    def test_merge_review_post_without_canonical_shows_error(self):
        """Submitting merge without picking a canonical author re-renders with an error."""
        response = self.client.post(
            reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk}),
            {"action": "merge"},
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please select the canonical author.", messages)
        self.assertTrue(Author.objects.filter(pk=self.author_b.pk).exists())

    def test_merge_review_post_merge_repoints_books_deletes_source_and_logs(self):
        """Merging repoints the source's books, deletes the source, and writes a MergeLog."""
        response = self.client.post(
            reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk}),
            {"action": "merge", "canonical": str(self.author_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:author-duplicates"))
        self.assertFalse(Author.objects.filter(pk=self.author_b.pk).exists())
        self.assertIn(self.author_a, self.book.authors.all())

        ct = ContentType.objects.get_for_model(Author)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.author_a.pk)
        self.assertEqual(log.merge_data["entity_type"], "author")
        self.assertEqual(log.merge_data["source_fields"]["surname"], "Kazantzaki")
        self.assertEqual(log.merge_data["repointed_book_ids"], [self.book.pk])
        self.assertEqual(log.merged_by, self.user)

    def test_merge_review_post_merge_into_b_deletes_a(self):
        """Picking the second author as canonical deletes the first instead."""
        response = self.client.post(
            reverse("curation:author-merge-review", kwargs={"a_id": self.author_a.pk, "b_id": self.author_b.pk}),
            {"action": "merge", "canonical": str(self.author_b.pk)},
        )

        self.assertRedirects(response, reverse("curation:author-duplicates"))
        self.assertFalse(Author.objects.filter(pk=self.author_a.pk).exists())
        self.assertTrue(Author.objects.filter(pk=self.author_b.pk).exists())


class TranslatorDuplicatesAndMergeTests(TestCase):
    """Tests for translator duplicate detection and merge review."""

    @classmethod
    def setUpTestData(cls):
        """Create two near-duplicate translators, one with a book."""
        cls.translator_a = Translator.objects.create(first_name="Nikos", surname="Stavrou")
        cls.translator_b = Translator.objects.create(first_name="Nikos", surname="Stavros")
        cls.book = BookEntry.objects.create(title="Report to Greco", offprint=False, has_cd=False, has_dvd=False)
        cls.book.translators.add(cls.translator_b)

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the duplicates list."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:translator-duplicates"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_pair_above_threshold(self):
        """The duplicates list finds the near-duplicate translator pair at a low threshold."""
        response = self.client.get(reverse("curation:translator-duplicates"), {"threshold": "0.1"})

        self.assertEqual(response.status_code, 200)
        merge_url = reverse(
            "curation:translator-merge-review",
            kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
        )
        self.assertContains(response, merge_url)

    def test_list_excludes_suppressed_pair_by_default(self):
        """A dismissed pair is hidden from the duplicates list unless requested."""
        ct = ContentType.objects.get_for_model(Translator)
        SuppressedPair.objects.create(
            content_type=ct,
            object_a_id=self.translator_a.pk,
            object_b_id=self.translator_b.pk,
            suppressed_by=self.user,
        )

        response = self.client.get(reverse("curation:translator-duplicates"), {"threshold": "0.1"})

        merge_url = reverse(
            "curation:translator-merge-review",
            kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
        )
        self.assertNotContains(response, merge_url)

    def test_list_include_suppressed_shows_dismissed_pair(self):
        """The show_suppressed flag brings a dismissed pair back into the list."""
        ct = ContentType.objects.get_for_model(Translator)
        SuppressedPair.objects.create(
            content_type=ct,
            object_a_id=self.translator_a.pk,
            object_b_id=self.translator_b.pk,
            suppressed_by=self.user,
        )

        response = self.client.get(
            reverse("curation:translator-duplicates"), {"threshold": "0.1", "show_suppressed": "1"}
        )

        merge_url = reverse(
            "curation:translator-merge-review",
            kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
        )
        self.assertContains(response, merge_url)

    def test_merge_review_get_shows_both_translators(self):
        """The merge review page renders both candidate translators."""
        response = self.client.get(
            reverse(
                "curation:translator-merge-review",
                kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stavrou")
        self.assertContains(response, "Stavros")

    def test_merge_review_post_suppress_dismisses_pair(self):
        """Dismissing a pair creates a SuppressedPair and leaves both translators intact."""
        response = self.client.post(
            reverse(
                "curation:translator-merge-review",
                kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
            ),
            {"action": "suppress"},
        )

        self.assertRedirects(response, reverse("curation:translator-duplicates"))
        ct = ContentType.objects.get_for_model(Translator)
        self.assertTrue(
            SuppressedPair.objects.filter(
                content_type=ct, object_a_id=self.translator_a.pk, object_b_id=self.translator_b.pk
            ).exists()
        )
        self.assertTrue(Translator.objects.filter(pk=self.translator_b.pk).exists())

    def test_merge_review_post_without_canonical_shows_error(self):
        """Submitting merge without picking a canonical translator re-renders with an error."""
        response = self.client.post(
            reverse(
                "curation:translator-merge-review",
                kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
            ),
            {"action": "merge"},
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please select the canonical translator.", messages)
        self.assertTrue(Translator.objects.filter(pk=self.translator_b.pk).exists())

    def test_merge_review_post_merge_repoints_books_deletes_source_and_logs(self):
        """Merging repoints the source's books, deletes the source, and writes a MergeLog."""
        response = self.client.post(
            reverse(
                "curation:translator-merge-review",
                kwargs={"a_id": self.translator_a.pk, "b_id": self.translator_b.pk},
            ),
            {"action": "merge", "canonical": str(self.translator_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:translator-duplicates"))
        self.assertFalse(Translator.objects.filter(pk=self.translator_b.pk).exists())
        self.assertIn(self.translator_a, self.book.translators.all())

        ct = ContentType.objects.get_for_model(Translator)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.translator_a.pk)
        self.assertEqual(log.merge_data["entity_type"], "translator")
        self.assertEqual(log.merge_data["source_fields"]["surname"], "Stavros")
        self.assertEqual(log.merge_data["repointed_book_ids"], [self.book.pk])
        self.assertEqual(log.merged_by, self.user)


class CuratorDuplicatesAndMergeTests(TestCase):
    """Tests for curator duplicate detection and merge review."""

    @classmethod
    def setUpTestData(cls):
        """Create two near-duplicate curators, one with a book."""
        cls.curator_a = Curator.objects.create(first_name="Eleni", surname="Papadaki")
        cls.curator_b = Curator.objects.create(first_name="Eleni", surname="Papadakis")
        cls.book = BookEntry.objects.create(title="Curated Anthology", offprint=False, has_cd=False, has_dvd=False)
        cls.book.curators.add(cls.curator_b)

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the duplicates list."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:curator-duplicates"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_pair_above_threshold(self):
        """The duplicates list finds the near-duplicate curator pair at a low threshold."""
        response = self.client.get(reverse("curation:curator-duplicates"), {"threshold": "0.1"})

        self.assertEqual(response.status_code, 200)
        merge_url = reverse(
            "curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk}
        )
        self.assertContains(response, merge_url)

    def test_list_excludes_suppressed_pair_by_default(self):
        """A dismissed pair is hidden from the duplicates list unless requested."""
        ct = ContentType.objects.get_for_model(Curator)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.curator_a.pk, object_b_id=self.curator_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:curator-duplicates"), {"threshold": "0.1"})

        merge_url = reverse(
            "curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk}
        )
        self.assertNotContains(response, merge_url)

    def test_list_include_suppressed_shows_dismissed_pair(self):
        """The show_suppressed flag brings a dismissed pair back into the list."""
        ct = ContentType.objects.get_for_model(Curator)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.curator_a.pk, object_b_id=self.curator_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:curator-duplicates"), {"threshold": "0.1", "show_suppressed": "1"})

        merge_url = reverse(
            "curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk}
        )
        self.assertContains(response, merge_url)

    def test_merge_review_get_shows_both_curators(self):
        """The merge review page renders both candidate curators."""
        response = self.client.get(
            reverse("curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Papadaki")
        self.assertContains(response, "Papadakis")

    def test_merge_review_post_suppress_dismisses_pair(self):
        """Dismissing a pair creates a SuppressedPair and leaves both curators intact."""
        response = self.client.post(
            reverse("curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk}),
            {"action": "suppress"},
        )

        self.assertRedirects(response, reverse("curation:curator-duplicates"))
        ct = ContentType.objects.get_for_model(Curator)
        self.assertTrue(
            SuppressedPair.objects.filter(
                content_type=ct, object_a_id=self.curator_a.pk, object_b_id=self.curator_b.pk
            ).exists()
        )
        self.assertTrue(Curator.objects.filter(pk=self.curator_b.pk).exists())

    def test_merge_review_post_without_canonical_shows_error(self):
        """Submitting merge without picking a canonical curator re-renders with an error."""
        response = self.client.post(
            reverse("curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk}),
            {"action": "merge"},
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please select the canonical curator.", messages)
        self.assertTrue(Curator.objects.filter(pk=self.curator_b.pk).exists())

    def test_merge_review_post_merge_repoints_books_deletes_source_and_logs(self):
        """Merging repoints the source's books, deletes the source, and writes a MergeLog."""
        response = self.client.post(
            reverse("curation:curator-merge-review", kwargs={"a_id": self.curator_a.pk, "b_id": self.curator_b.pk}),
            {"action": "merge", "canonical": str(self.curator_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:curator-duplicates"))
        self.assertFalse(Curator.objects.filter(pk=self.curator_b.pk).exists())
        self.assertIn(self.curator_a, self.book.curators.all())

        ct = ContentType.objects.get_for_model(Curator)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.curator_a.pk)
        self.assertEqual(log.merge_data["entity_type"], "curator")
        self.assertEqual(log.merge_data["source_fields"]["surname"], "Papadakis")
        self.assertEqual(log.merge_data["repointed_book_ids"], [self.book.pk])
        self.assertEqual(log.merged_by, self.user)


class TopicDuplicatesAndMergeTests(TestCase):
    """Tests for topic duplicate detection and merge review."""

    @classmethod
    def setUpTestData(cls):
        """Create two near-duplicate topics, one with a book."""
        cls.topic_a = Topic.objects.create(topic_name="Greek Mythology")
        cls.topic_b = Topic.objects.create(topic_name="Greek Mythologies")
        cls.book = BookEntry.objects.create(title="Gods and Heroes", offprint=False, has_cd=False, has_dvd=False)
        cls.book.topics.add(cls.topic_b)

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the duplicates list."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:topic-duplicates"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_pair_above_threshold(self):
        """The duplicates list finds the near-duplicate topic pair at a low threshold."""
        response = self.client.get(reverse("curation:topic-duplicates"), {"threshold": "0.1"})

        self.assertEqual(response.status_code, 200)
        merge_url = reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk})
        self.assertContains(response, merge_url)

    def test_list_excludes_suppressed_pair_by_default(self):
        """A dismissed pair is hidden from the duplicates list unless requested."""
        ct = ContentType.objects.get_for_model(Topic)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.topic_a.pk, object_b_id=self.topic_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:topic-duplicates"), {"threshold": "0.1"})

        merge_url = reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk})
        self.assertNotContains(response, merge_url)

    def test_list_include_suppressed_shows_dismissed_pair(self):
        """The show_suppressed flag brings a dismissed pair back into the list."""
        ct = ContentType.objects.get_for_model(Topic)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.topic_a.pk, object_b_id=self.topic_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:topic-duplicates"), {"threshold": "0.1", "show_suppressed": "1"})

        merge_url = reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk})
        self.assertContains(response, merge_url)

    def test_merge_review_get_shows_both_topics(self):
        """The merge review page renders both candidate topics."""
        response = self.client.get(
            reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Greek Mythology")
        self.assertContains(response, "Greek Mythologies")

    def test_merge_review_post_suppress_dismisses_pair(self):
        """Dismissing a pair creates a SuppressedPair and leaves both topics intact."""
        response = self.client.post(
            reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk}),
            {"action": "suppress"},
        )

        self.assertRedirects(response, reverse("curation:topic-duplicates"))
        ct = ContentType.objects.get_for_model(Topic)
        self.assertTrue(
            SuppressedPair.objects.filter(
                content_type=ct, object_a_id=self.topic_a.pk, object_b_id=self.topic_b.pk
            ).exists()
        )
        self.assertTrue(Topic.objects.filter(pk=self.topic_b.pk).exists())

    def test_merge_review_post_without_canonical_shows_error(self):
        """Submitting merge without picking a canonical topic re-renders with an error."""
        response = self.client.post(
            reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk}),
            {"action": "merge"},
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please select the canonical topic.", messages)
        self.assertTrue(Topic.objects.filter(pk=self.topic_b.pk).exists())

    def test_merge_review_post_merge_repoints_books_deletes_source_and_logs(self):
        """Merging repoints the source's books, deletes the source, and writes a MergeLog."""
        response = self.client.post(
            reverse("curation:topic-merge-review", kwargs={"a_id": self.topic_a.pk, "b_id": self.topic_b.pk}),
            {"action": "merge", "canonical": str(self.topic_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:topic-duplicates"))
        self.assertFalse(Topic.objects.filter(pk=self.topic_b.pk).exists())
        self.assertIn(self.topic_a, self.book.topics.all())

        ct = ContentType.objects.get_for_model(Topic)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.topic_a.pk)
        self.assertEqual(log.merge_data["entity_type"], "topic")
        self.assertEqual(log.merge_data["source_fields"]["topic_name"], "Greek Mythologies")
        self.assertEqual(log.merge_data["repointed_book_ids"], [self.book.pk])
        self.assertEqual(log.merged_by, self.user)


class EditorDuplicatesAndMergeTests(TestCase):
    """Tests for editor duplicate detection and merge review."""

    @classmethod
    def setUpTestData(cls):
        """Create two near-duplicate editors, one with a book pointing to it by FK."""
        cls.editor_a = Editor.objects.create(name="Kastaniotis")
        cls.editor_b = Editor.objects.create(name="Kastanioti")
        cls.book = BookEntry.objects.create(
            title="Athens Nights", offprint=False, has_cd=False, has_dvd=False, editor=cls.editor_b
        )

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the duplicates list."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:editor-duplicates"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_pair_above_threshold(self):
        """The duplicates list finds the near-duplicate editor pair at a low threshold."""
        response = self.client.get(reverse("curation:editor-duplicates"), {"threshold": "0.1"})

        self.assertEqual(response.status_code, 200)
        merge_url = reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk})
        self.assertContains(response, merge_url)

    def test_list_excludes_suppressed_pair_by_default(self):
        """A dismissed pair is hidden from the duplicates list unless requested."""
        ct = ContentType.objects.get_for_model(Editor)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.editor_a.pk, object_b_id=self.editor_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:editor-duplicates"), {"threshold": "0.1"})

        merge_url = reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk})
        self.assertNotContains(response, merge_url)

    def test_list_include_suppressed_shows_dismissed_pair(self):
        """The show_suppressed flag brings a dismissed pair back into the list."""
        ct = ContentType.objects.get_for_model(Editor)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.editor_a.pk, object_b_id=self.editor_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:editor-duplicates"), {"threshold": "0.1", "show_suppressed": "1"})

        merge_url = reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk})
        self.assertContains(response, merge_url)

    def test_merge_review_get_shows_both_editors(self):
        """The merge review page renders both candidate editors."""
        response = self.client.get(
            reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kastaniotis")
        self.assertContains(response, "Kastanioti")

    def test_merge_review_post_suppress_dismisses_pair(self):
        """Dismissing a pair creates a SuppressedPair and leaves both editors intact."""
        response = self.client.post(
            reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk}),
            {"action": "suppress"},
        )

        self.assertRedirects(response, reverse("curation:editor-duplicates"))
        ct = ContentType.objects.get_for_model(Editor)
        self.assertTrue(
            SuppressedPair.objects.filter(
                content_type=ct, object_a_id=self.editor_a.pk, object_b_id=self.editor_b.pk
            ).exists()
        )
        self.assertTrue(Editor.objects.filter(pk=self.editor_b.pk).exists())

    def test_merge_review_post_without_canonical_shows_error(self):
        """Submitting merge without picking a canonical editor re-renders with an error."""
        response = self.client.post(
            reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk}),
            {"action": "merge"},
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please select the canonical editor.", messages)
        self.assertTrue(Editor.objects.filter(pk=self.editor_b.pk).exists())

    def test_merge_review_post_merge_repoints_books_by_fk_deletes_source_and_logs(self):
        """Merging re-points the source's books via the editor FK, deletes the source, and writes a MergeLog."""
        response = self.client.post(
            reverse("curation:editor-merge-review", kwargs={"a_id": self.editor_a.pk, "b_id": self.editor_b.pk}),
            {"action": "merge", "canonical": str(self.editor_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:editor-duplicates"))
        self.assertFalse(Editor.objects.filter(pk=self.editor_b.pk).exists())
        self.book.refresh_from_db()
        self.assertEqual(self.book.editor_id, self.editor_a.pk)

        ct = ContentType.objects.get_for_model(Editor)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.editor_a.pk)
        self.assertEqual(log.merge_data["entity_type"], "editor")
        self.assertEqual(log.merge_data["source_fields"]["name"], "Kastanioti")
        self.assertEqual(log.merge_data["repointed_book_ids"], [self.book.pk])
        self.assertEqual(log.merged_by, self.user)


class BookDuplicatesAndMergeTests(TestCase):
    """Tests for book entry duplicate detection and merge review, including field conflicts."""

    @classmethod
    def setUpTestData(cls):
        """Create two near-duplicate book entries with conflicting scalar/boolean fields and distinct relations."""
        cls.author_x = Author.objects.create(surname="Author X")
        cls.author_y = Author.objects.create(surname="Author Y")
        cls.book_a = BookEntry.objects.create(
            title="Zorba the Greek",
            subtitle="A novel",
            offprint=False,
            has_cd=False,
            has_dvd=False,
            pages=300,
        )
        cls.book_b = BookEntry.objects.create(
            title="Zorba the Greek",
            subtitle="An epic novel",
            offprint=False,
            has_cd=True,
            has_dvd=False,
            pages=350,
        )
        cls.book_a.authors.add(cls.author_x)
        cls.book_b.authors.add(cls.author_y)
        cls.entry_number_a = EntryNumber.objects.create(entry_number=1001, book_entry=cls.book_a, copies=1)
        cls.entry_number_b = EntryNumber.objects.create(entry_number=1002, book_entry=cls.book_b, copies=1)

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_curate is denied access to the duplicates list."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:book-duplicates"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_pair_above_threshold(self):
        """The duplicates list finds the near-duplicate book pair at a low threshold."""
        response = self.client.get(reverse("curation:book-duplicates"), {"threshold": "0.1"})

        self.assertEqual(response.status_code, 200)
        merge_url = reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk})
        self.assertContains(response, merge_url)

    def test_list_excludes_suppressed_pair_by_default(self):
        """A dismissed pair is hidden from the duplicates list unless requested."""
        ct = ContentType.objects.get_for_model(BookEntry)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.book_a.pk, object_b_id=self.book_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:book-duplicates"), {"threshold": "0.1"})

        merge_url = reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk})
        self.assertNotContains(response, merge_url)

    def test_list_include_suppressed_shows_dismissed_pair(self):
        """The show_suppressed flag brings a dismissed pair back into the list."""
        ct = ContentType.objects.get_for_model(BookEntry)
        SuppressedPair.objects.create(
            content_type=ct, object_a_id=self.book_a.pk, object_b_id=self.book_b.pk, suppressed_by=self.user
        )

        response = self.client.get(reverse("curation:book-duplicates"), {"threshold": "0.1", "show_suppressed": "1"})

        merge_url = reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk})
        self.assertContains(response, merge_url)

    def test_merge_review_get_shows_conflicting_fields(self):
        """The merge review page lists the conflicting scalar fields for resolution."""
        response = self.client.get(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field_subtitle")
        self.assertContains(response, "field_pages")

    def test_merge_review_post_suppress_dismisses_pair(self):
        """Dismissing a pair creates a SuppressedPair and leaves both book entries intact."""
        response = self.client.post(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk}),
            {"action": "suppress"},
        )

        self.assertRedirects(response, reverse("curation:book-duplicates"))
        ct = ContentType.objects.get_for_model(BookEntry)
        self.assertTrue(
            SuppressedPair.objects.filter(
                content_type=ct, object_a_id=self.book_a.pk, object_b_id=self.book_b.pk
            ).exists()
        )
        self.assertTrue(BookEntry.objects.filter(pk=self.book_b.pk).exists())

    def test_merge_review_post_without_canonical_shows_error(self):
        """Submitting merge without picking a canonical book entry re-renders with an error."""
        response = self.client.post(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk}),
            {"action": "merge"},
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please select the canonical book entry.", messages)
        self.assertTrue(BookEntry.objects.filter(pk=self.book_b.pk).exists())

    def test_merge_review_post_default_keeps_target_scalar_values(self):
        """Without explicit field choices, the canonical entry's own scalar values win."""
        response = self.client.post(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk}),
            {"action": "merge", "canonical": str(self.book_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:book-duplicates"))
        self.book_a.refresh_from_db()
        self.assertEqual(self.book_a.subtitle, "A novel")
        self.assertEqual(self.book_a.pages, 300)

    def test_merge_review_post_selecting_b_uses_source_scalar_value(self):
        """Explicitly choosing the source's value for a field applies it to the canonical entry."""
        response = self.client.post(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk}),
            {
                "action": "merge",
                "canonical": str(self.book_a.pk),
                "field_subtitle": "b",
                "field_pages": "b",
            },
        )

        self.assertRedirects(response, reverse("curation:book-duplicates"))
        self.book_a.refresh_from_db()
        self.assertEqual(self.book_a.subtitle, "An epic novel")
        self.assertEqual(self.book_a.pages, 350)

        ct = ContentType.objects.get_for_model(BookEntry)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.book_a.pk)
        self.assertEqual(log.merge_data["target_fields_before"]["subtitle"], "A novel")
        self.assertEqual(log.merge_data["target_fields_before"]["pages"], 300)

    def test_merge_review_post_boolean_true_wins(self):
        """A boolean field is set to True on the canonical entry if either side had it set."""
        response = self.client.post(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk}),
            {"action": "merge", "canonical": str(self.book_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:book-duplicates"))
        self.book_a.refresh_from_db()
        self.assertTrue(self.book_a.has_cd)

    def test_merge_review_post_unions_m2m_and_repoints_entry_numbers(self):
        """Merging unions the M2M relations and re-points the source's entry numbers to the canonical entry."""
        response = self.client.post(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk}),
            {"action": "merge", "canonical": str(self.book_a.pk)},
        )

        self.assertRedirects(response, reverse("curation:book-duplicates"))
        self.assertFalse(BookEntry.objects.filter(pk=self.book_b.pk).exists())
        self.assertIn(self.author_y, self.book_a.authors.all())
        self.entry_number_b.refresh_from_db()
        self.assertEqual(self.entry_number_b.book_entry_id, self.book_a.pk)

        ct = ContentType.objects.get_for_model(BookEntry)
        log = MergeLog.objects.get(content_type=ct, target_object_id=self.book_a.pk)
        self.assertEqual(log.merge_data["entity_type"], "book")
        self.assertEqual(log.merge_data["added_m2m_to_target"]["authors"], [self.author_y.pk])
        self.assertEqual(log.merge_data["repointed_entry_number_ids"], [self.entry_number_b.pk])
        self.assertEqual(log.merged_by, self.user)

    def test_merge_review_shows_active_loan_warning(self):
        """The merge review page warns about active loans on either candidate entry."""
        customer = Customer.objects.create(
            first_name="Maria",
            surname="Reader",
            id_type=Customer.ID_TYPE_ID_CARD,
            id_number="A1",
            phone_number="2100000000",
            email="maria@example.com",
        )
        Loan.objects.create(
            customer=customer,
            entry_number=self.entry_number_b,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 1),
            expected_end=datetime.date(2026, 6, 15),
        )

        response = self.client.get(
            reverse("curation:book-merge-review", kwargs={"a_id": self.book_a.pk, "b_id": self.book_b.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "active loan")
