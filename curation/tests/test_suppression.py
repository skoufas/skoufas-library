"""Tests for removing a dismissal (unsuppress) across all suppressible entity types."""

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from books.models import Author
from books.models import BookEntry
from books.models import Curator
from books.models import Editor
from books.models import Topic
from books.models import Translator
from curation.models import SuppressedPair


def _grant_can_curate(user):
    user.user_permissions.add(Permission.objects.get(codename="can_curate"))


class SuppressedPairUnsuppressViewTests(TestCase):
    """Tests for undoing a dismissal, redirecting back to the right duplicates list per entity type."""

    def setUp(self):
        """Log in a curator with the can_curate permission."""
        self.user = User.objects.create_user(username="curator", password="password")
        _grant_can_curate(self.user)
        self.client.force_login(self.user)

    def _suppress(self, model_class, obj_a, obj_b):
        ct = ContentType.objects.get_for_model(model_class)
        return SuppressedPair.objects.create(
            content_type=ct, object_a_id=obj_a.pk, object_b_id=obj_b.pk, suppressed_by=self.user
        )

    def test_denies_without_permission(self):
        """A user lacking can_curate is denied access to unsuppress a pair."""
        author_a = Author.objects.create(surname="A")
        author_b = Author.objects.create(surname="B")
        pair = self._suppress(Author, author_a, author_b)
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertEqual(response.status_code, 403)

    def test_unsuppress_author_pair_redirects_to_author_duplicates(self):
        """Unsuppressing an author pair deletes it and redirects to the author duplicates list."""
        author_a = Author.objects.create(surname="A")
        author_b = Author.objects.create(surname="B")
        pair = self._suppress(Author, author_a, author_b)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertRedirects(response, reverse("curation:author-duplicates"))
        self.assertFalse(SuppressedPair.objects.filter(pk=pair.pk).exists())

    def test_unsuppress_book_pair_redirects_to_book_duplicates(self):
        """Unsuppressing a book entry pair deletes it and redirects to the book duplicates list."""
        book_a = BookEntry.objects.create(title="A", offprint=False, has_cd=False, has_dvd=False)
        book_b = BookEntry.objects.create(title="B", offprint=False, has_cd=False, has_dvd=False)
        pair = self._suppress(BookEntry, book_a, book_b)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertRedirects(response, reverse("curation:book-duplicates"))
        self.assertFalse(SuppressedPair.objects.filter(pk=pair.pk).exists())

    def test_unsuppress_translator_pair_redirects_to_translator_duplicates(self):
        """Unsuppressing a translator pair deletes it and redirects to the translator duplicates list."""
        translator_a = Translator.objects.create(surname="A")
        translator_b = Translator.objects.create(surname="B")
        pair = self._suppress(Translator, translator_a, translator_b)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertRedirects(response, reverse("curation:translator-duplicates"))
        self.assertFalse(SuppressedPair.objects.filter(pk=pair.pk).exists())

    def test_unsuppress_curator_pair_redirects_to_curator_duplicates(self):
        """Unsuppressing a curator pair deletes it and redirects to the curator duplicates list."""
        curator_a = Curator.objects.create(surname="A")
        curator_b = Curator.objects.create(surname="B")
        pair = self._suppress(Curator, curator_a, curator_b)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertRedirects(response, reverse("curation:curator-duplicates"))
        self.assertFalse(SuppressedPair.objects.filter(pk=pair.pk).exists())

    def test_unsuppress_topic_pair_redirects_to_topic_duplicates(self):
        """Unsuppressing a topic pair deletes it and redirects to the topic duplicates list."""
        topic_a = Topic.objects.create(topic_name="A")
        topic_b = Topic.objects.create(topic_name="B")
        pair = self._suppress(Topic, topic_a, topic_b)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertRedirects(response, reverse("curation:topic-duplicates"))
        self.assertFalse(SuppressedPair.objects.filter(pk=pair.pk).exists())

    def test_unsuppress_editor_pair_redirects_to_editor_duplicates(self):
        """Unsuppressing an editor pair deletes it and redirects to the editor duplicates list."""
        editor_a = Editor.objects.create(name="A")
        editor_b = Editor.objects.create(name="B")
        pair = self._suppress(Editor, editor_a, editor_b)

        response = self.client.post(reverse("curation:unsuppress-pair", kwargs={"pair_id": pair.pk}))

        self.assertRedirects(response, reverse("curation:editor-duplicates"))
        self.assertFalse(SuppressedPair.objects.filter(pk=pair.pk).exists())
