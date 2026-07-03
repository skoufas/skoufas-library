"""Tests for the public browse/detail views in the books app."""

import cv2
import numpy as np
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from books.models import Author
from books.models import BookEntry
from books.models import Donor
from books.models import EntryNumber
from books.models import Location


def _build_cover_image_bytes() -> bytes:
    """Encode a light background with a dark rectangle (simulated book) as a JPEG."""
    img = np.full((300, 400, 3), 220, dtype=np.uint8)
    cv2.rectangle(img, (80, 40), (320, 260), (20, 20, 20), thickness=-1)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


class BookEntryViewTests(TestCase):
    """Smoke tests for the catalogue browse and detail views."""

    @classmethod
    def setUpTestData(cls):
        """Create a book with an author, donor, entry number, and location."""
        cls.author = Author.objects.create(first_name="Odysseas", surname="Elytis")
        cls.donor = Donor.objects.create(first_name="Maria", surname="Papadopoulou")
        cls.building = Location.objects.create(name="Main Building", type=Location.TYPE_BUILDING)
        cls.shelf = Location.objects.create(name="Shelf 1", type=Location.TYPE_SHELF, parent=cls.building)
        cls.book_entry = BookEntry.objects.create(
            title="The Axion Esti",
            subtitle="A poem",
            offprint=False,
            has_cd=False,
            has_dvd=False,
            skoufas_classification="800",
        )
        cls.book_entry.authors.add(cls.author)
        cls.book_entry.entry_donors.add(cls.donor)
        cls.entry_number = EntryNumber.objects.create(
            entry_number=1001,
            book_entry=cls.book_entry,
            location=cls.shelf,
        )

    def test_book_list(self):
        """The catalogue root page lists known books."""
        response = self.client.get(reverse("books:book-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_book_detail(self):
        """A book's detail page renders its own title."""
        response = self.client.get(reverse("books:book-by-id", kwargs={"pk": self.book_entry.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_book_by_entry_number(self):
        """Looking a book up by entry number reuses the book detail template."""
        response = self.client.get(reverse("books:book-by-entry-number", kwargs={"pk": self.entry_number.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_book_by_skoufas_main_class(self):
        """Filtering by main class returns books with a matching classification_class."""
        response = self.client.get(reverse("books:book-by-skoufas-main-class", kwargs={"classification_class": 800}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_book_by_skoufas_main_class_none_matches_unclassified_books(self):
        """The literal string "None" in the URL is treated as Python None, not the text "None"."""
        unclassified = BookEntry.objects.create(title="Unclassified book", offprint=False, has_cd=False, has_dvd=False)

        response = self.client.get(reverse("books:book-by-skoufas-main-class", kwargs={"classification_class": "None"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, unclassified.title)
        self.assertNotContains(response, "The Axion Esti")

    def test_book_by_skoufas_classification(self):
        """Filtering by the full classification string returns an exact match."""
        response = self.client.get(
            reverse("books:book-by-skoufas-classification", kwargs={"skoufas_classification": "800"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_author_list(self):
        """The author list page renders known authors."""
        response = self.client.get(reverse("books:author-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elytis")

    def test_author_detail(self):
        """An author's detail page lists their books."""
        response = self.client.get(reverse("books:author-by-id", kwargs={"pk": self.author.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_donor_list(self):
        """The donor list page renders known donors."""
        response = self.client.get(reverse("books:donor-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Papadopoulou")

    def test_donor_detail(self):
        """A donor's detail page lists the books they donated."""
        response = self.client.get(reverse("books:donor-by-id", kwargs={"pk": self.donor.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Axion Esti")

    def test_class_list(self):
        """The classification overview groups books under their classification code."""
        response = self.client.get(reverse("books:skoufas-class-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "800")

    def test_location_list(self):
        """The top-level location list renders public buildings."""
        response = self.client.get(reverse("books:location-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main Building")

    def test_location_detail(self):
        """A location's detail page renders its name and descendant entry numbers."""
        response = self.client.get(reverse("books:location-by-id", kwargs={"pk": self.building.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main Building")
        self.assertContains(response, "The Axion Esti")

    def test_location_detail_non_public_blocked_without_permission(self):
        """A non-public location is hidden from users without view_nonpublic_location."""
        restricted = Location.objects.create(
            name="Restricted Room", type=Location.TYPE_ROOM, parent=self.building, non_public=True
        )

        response = self.client.get(reverse("books:location-by-id", kwargs={"pk": restricted.pk}))

        self.assertEqual(response.status_code, 403)

    def test_location_detail_non_public_visible_with_permission(self):
        """A non-public location is reachable by users granted view_nonpublic_location."""
        restricted = Location.objects.create(
            name="Restricted Room", type=Location.TYPE_ROOM, parent=self.building, non_public=True
        )
        user = User.objects.create_user(username="staff", password="password", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_nonpublic_location"))
        self.client.force_login(user)

        response = self.client.get(reverse("books:location-by-id", kwargs={"pk": restricted.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Restricted Room")


class BookEntryCoverDetectViewTests(TestCase):
    """Tests for the cover-image contour detection endpoint."""

    def setUp(self):
        """Log in a user without curation.can_inventory by default."""
        self.user = User.objects.create_user(username="inventory", password="password", is_staff=True)
        self.client.force_login(self.user)

    def _grant_can_inventory(self):
        """Grant the permission required to use the detection endpoint."""
        self.user.user_permissions.add(Permission.objects.get(codename="can_inventory"))

    def test_detect_cover_returns_sane_crop_box(self):
        """A valid image produces a crop box that fits within the image bounds."""
        self._grant_can_inventory()
        image = SimpleUploadedFile("cover.jpg", _build_cover_image_bytes(), content_type="image/jpeg")

        response = self.client.post(reverse("books:book-cover-detect"), {"image": image})

        self.assertEqual(response.status_code, 200)
        box = response.json()
        self.assertEqual(set(box), {"x", "y", "width", "height"})
        self.assertGreaterEqual(box["x"], 0)
        self.assertGreaterEqual(box["y"], 0)
        self.assertGreater(box["width"], 0)
        self.assertGreater(box["height"], 0)
        self.assertLessEqual(box["x"] + box["width"], 400)
        self.assertLessEqual(box["y"] + box["height"], 300)

    def test_detect_cover_requires_permission(self):
        """Users without curation.can_inventory cannot use the detection endpoint."""
        image = SimpleUploadedFile("cover.jpg", _build_cover_image_bytes(), content_type="image/jpeg")

        response = self.client.post(reverse("books:book-cover-detect"), {"image": image})

        self.assertEqual(response.status_code, 403)

    def test_detect_cover_missing_image(self):
        """A request without an image file is rejected."""
        self._grant_can_inventory()

        response = self.client.post(reverse("books:book-cover-detect"), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "no image"})

    def test_detect_cover_invalid_image(self):
        """Non-image bytes are rejected."""
        self._grant_can_inventory()
        garbage = SimpleUploadedFile("not-an-image.jpg", b"not an image", content_type="image/jpeg")

        response = self.client.post(reverse("books:book-cover-detect"), {"image": garbage})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid image"})
