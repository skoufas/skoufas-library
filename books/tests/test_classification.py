"""Tests for the Dewey classification lookup."""

from django.test import SimpleTestCase
from django.utils.translation import override

from books.skoufas_classification_classes import classification


class ClassificationTests(SimpleTestCase):
    """Tests for classification()."""

    def test_none_has_no_description(self):
        """A missing class number has no description."""
        self.assertIsNone(classification(None))

    def test_zero_is_a_valid_class(self):
        """Class 0 (computer science) is described, not treated as missing."""
        self.assertEqual(str(classification(0)), "Computer science, information and general works")

    def test_decimal_class(self):
        """A three digit class number resolves to its decimal class."""
        self.assertEqual(str(classification(150)), "Psychology")

    def test_unknown_number_keeps_original_value(self):
        """An unknown number is reported as given, not rounded down."""
        with override("en"):
            self.assertEqual(str(classification(1234)), "Unknown skoufas classification number: 1234")
