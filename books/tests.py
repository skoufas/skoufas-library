"""Tests on Book."""

from django.test import TestCase

from books.models import BookEntry
from books.models import EntryNumber


class EntryNumberTests(TestCase):
    """Tests for EntryNumber defaults."""

    def test_copies_defaults_to_one(self):
        """A new entry number defaults to a single available copy."""
        book_entry = BookEntry.objects.create(title="Default copies test", offprint=False, has_cd=False, has_dvd=False)
        entry_number = EntryNumber.objects.create(entry_number=999001, book_entry=book_entry)

        self.assertEqual(entry_number.copies, 1)
