"""Tests for the physical inventory workflow: sessions, scanning, confirmation, and close-out."""

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from books.models import BookEntry
from books.models import EntryNumber
from books.models import Location
from curation.models import InventorySession
from curation.models import InventorySessionEntry


def _grant_can_inventory(user):
    user.user_permissions.add(Permission.objects.get(codename="can_inventory"))


class InventorySessionListViewTests(TestCase):
    """Tests for the inventory hub: listing sessions and starting a new one."""

    @classmethod
    def setUpTestData(cls):
        """Create a shelf and a box (leaf locations) plus a non-leaf building."""
        cls.building = Location.objects.create(name="Main Building", type=Location.TYPE_BUILDING)
        cls.shelf = Location.objects.create(name="Shelf 1", type=Location.TYPE_SHELF, parent=cls.building)
        cls.box = Location.objects.create(name="Box 1", type=Location.TYPE_BOX, parent=cls.building)

    def setUp(self):
        """Log in a staff user with the can_inventory permission."""
        self.user = User.objects.create_user(username="stocktaker", password="password")
        _grant_can_inventory(self.user)
        self.client.force_login(self.user)

    def test_list_denies_without_permission(self):
        """A user lacking can_inventory is denied access to the inventory hub."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:inventory-list"))

        self.assertEqual(response.status_code, 403)

    def test_list_shows_open_sessions_and_leaf_locations(self):
        """The hub lists open sessions and offers only leaf locations to start a new one."""
        InventorySession.objects.create(location=self.shelf, started_by=self.user)

        response = self.client.get(reverse("curation:inventory-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shelf 1")
        self.assertContains(response, "Box 1")
        self.assertNotIn(self.building, response.context["leaf_locations"])

    def test_post_starts_new_session_for_leaf_location_and_redirects_to_scan(self):
        """Starting a session for a shelf creates it and redirects to the scan screen."""
        response = self.client.post(reverse("curation:inventory-list"), {"location_id": str(self.shelf.pk)})

        session = InventorySession.objects.get(location=self.shelf)
        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": session.pk}))
        self.assertTrue(session.is_open)
        self.assertEqual(session.started_by, self.user)

    def test_post_rejects_non_leaf_location(self):
        """Starting a session for a non-leaf location (a building) is rejected."""
        response = self.client.post(reverse("curation:inventory-list"), {"location_id": str(self.building.pk)})

        self.assertRedirects(response, reverse("curation:inventory-list"))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Only Shelf or Box locations can be inventoried.", messages)
        self.assertFalse(InventorySession.objects.filter(location=self.building).exists())

    def test_post_when_open_session_exists_redirects_to_existing_session(self):
        """Starting a session for a location with an already-open session redirects to that session instead."""
        existing = InventorySession.objects.create(location=self.shelf, started_by=self.user)

        response = self.client.post(reverse("curation:inventory-list"), {"location_id": str(self.shelf.pk)})

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": existing.pk}))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("An open inventory session already exists for this location.", messages)
        self.assertEqual(InventorySession.objects.filter(location=self.shelf).count(), 1)


class InventorySessionScanViewTests(TestCase):
    """Tests for the scan screen: looking up entry numbers and staging pending confirmation."""

    @classmethod
    def setUpTestData(cls):
        """Create an open session for a shelf, and an entry number currently on a different shelf."""
        cls.building = Location.objects.create(name="Main Building", type=Location.TYPE_BUILDING)
        cls.shelf = Location.objects.create(name="Shelf 1", type=Location.TYPE_SHELF, parent=cls.building)
        cls.other_shelf = Location.objects.create(name="Shelf 2", type=Location.TYPE_SHELF, parent=cls.building)
        cls.book = BookEntry.objects.create(title="Scanned Book", offprint=False, has_cd=False, has_dvd=False)
        cls.entry_number = EntryNumber.objects.create(entry_number=2001, book_entry=cls.book, location=cls.other_shelf)

    def setUp(self):
        """Log in a staff user with the can_inventory permission, and open a session for the shelf."""
        self.user = User.objects.create_user(username="stocktaker", password="password")
        _grant_can_inventory(self.user)
        self.client.force_login(self.user)
        self.session = InventorySession.objects.create(location=self.shelf, started_by=self.user)

    def test_scan_denies_without_permission(self):
        """A user lacking can_inventory is denied access to the scan screen."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 403)

    def test_scan_get_on_closed_session_404s(self):
        """The scan screen for an already-closed session is not found."""
        self.session.closed_at = timezone.now()
        self.session.save(update_fields=["closed_at"])

        response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 404)

    def test_scan_post_empty_value_shows_error(self):
        """Submitting the scan form without a value shows an error."""
        response = self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}), {"entry_number": ""}
        )

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Please enter an entry number.", messages)

    def test_scan_post_unknown_value_shows_error(self):
        """Scanning an entry number that doesn't exist shows an error."""
        response = self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}), {"entry_number": "999999"}
        )

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn('Entry number "999999" not found in the database.', messages)

    def test_scan_post_non_numeric_value_shows_error(self):
        """Scanning a non-numeric value is treated the same as not-found."""
        response = self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}), {"entry_number": "abc"}
        )

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn('Entry number "abc" not found in the database.', messages)

    def test_scan_post_valid_entry_stages_pending_with_conflict(self):
        """Scanning a valid entry number currently at a different location flags a conflict."""
        response = self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}),
            {"entry_number": str(self.entry_number.entry_number)},
        )

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        get_response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        self.assertContains(get_response, "Scanned Book")
        self.assertContains(get_response, "Confirming will move it")

    def test_scan_get_clears_pending_entry_deleted_since_scan(self):
        """If the pending entry number was deleted after being scanned, the pending panel is cleared."""
        self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}),
            {"entry_number": str(self.entry_number.entry_number)},
        )
        self.entry_number.delete()

        response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Confirm this book?")

    def test_scan_post_valid_entry_without_conflict_when_already_at_session_location(self):
        """Scanning an entry number already at the session's own location does not flag a conflict."""
        self.entry_number.location = self.shelf
        self.entry_number.save(update_fields=["location"])

        response = self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}),
            {"entry_number": str(self.entry_number.entry_number)},
        )

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        get_response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        self.assertContains(get_response, "Scanned Book")
        self.assertNotContains(get_response, "Confirming will move it")


class InventorySessionConfirmViewTests(TestCase):
    """Tests for confirming a scanned entry into the session's location."""

    @classmethod
    def setUpTestData(cls):
        """Create an open session for a shelf and an entry number currently on a different shelf."""
        cls.building = Location.objects.create(name="Main Building", type=Location.TYPE_BUILDING)
        cls.shelf = Location.objects.create(name="Shelf 1", type=Location.TYPE_SHELF, parent=cls.building)
        cls.other_shelf = Location.objects.create(name="Shelf 2", type=Location.TYPE_SHELF, parent=cls.building)
        cls.book = BookEntry.objects.create(title="Scanned Book", offprint=False, has_cd=False, has_dvd=False)
        cls.entry_number = EntryNumber.objects.create(entry_number=2001, book_entry=cls.book, location=cls.other_shelf)

    def setUp(self):
        """Log in a staff user with the can_inventory permission, and open a session for the shelf."""
        self.user = User.objects.create_user(username="stocktaker", password="password")
        _grant_can_inventory(self.user)
        self.client.force_login(self.user)
        self.session = InventorySession.objects.create(location=self.shelf, started_by=self.user)

    def test_confirm_denies_without_permission(self):
        """A user lacking can_inventory is denied access to confirm an entry."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.post(reverse("curation:inventory-confirm", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 403)

    def test_confirm_without_pending_scan_shows_error(self):
        """Confirming without a prior scan shows an error."""
        response = self.client.post(reverse("curation:inventory-confirm", kwargs={"pk": self.session.pk}))

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("No pending scan to confirm.", messages)

    def test_confirm_assigns_location_and_records_previous_location(self):
        """Confirming a pending scan moves the entry number to the session's location, recording where it was."""
        self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}),
            {"entry_number": str(self.entry_number.entry_number)},
        )

        response = self.client.post(reverse("curation:inventory-confirm", kwargs={"pk": self.session.pk}))

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        self.entry_number.refresh_from_db()
        self.assertEqual(self.entry_number.location, self.shelf)
        session_entry = InventorySessionEntry.objects.get(session=self.session, entry_number=self.entry_number)
        self.assertEqual(session_entry.outcome, InventorySessionEntry.OUTCOME_CONFIRMED)
        self.assertEqual(session_entry.previous_location, self.other_shelf)

        get_response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        self.assertNotContains(get_response, "Confirm this book?")

    def test_confirm_records_no_previous_location_when_already_unassigned_and_matching(self):
        """Confirming an entry already at the session's location records no previous_location."""
        self.entry_number.location = self.shelf
        self.entry_number.save(update_fields=["location"])
        self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}),
            {"entry_number": str(self.entry_number.entry_number)},
        )

        self.client.post(reverse("curation:inventory-confirm", kwargs={"pk": self.session.pk}))

        session_entry = InventorySessionEntry.objects.get(session=self.session, entry_number=self.entry_number)
        self.assertIsNone(session_entry.previous_location)


class InventorySessionSetAsideViewTests(TestCase):
    """Tests for setting aside a scanned entry without changing its location."""

    @classmethod
    def setUpTestData(cls):
        """Create an open session for a shelf and an entry number currently on a different shelf."""
        cls.building = Location.objects.create(name="Main Building", type=Location.TYPE_BUILDING)
        cls.shelf = Location.objects.create(name="Shelf 1", type=Location.TYPE_SHELF, parent=cls.building)
        cls.other_shelf = Location.objects.create(name="Shelf 2", type=Location.TYPE_SHELF, parent=cls.building)
        cls.book = BookEntry.objects.create(title="Scanned Book", offprint=False, has_cd=False, has_dvd=False)
        cls.entry_number = EntryNumber.objects.create(entry_number=2001, book_entry=cls.book, location=cls.other_shelf)

    def setUp(self):
        """Log in a staff user with the can_inventory permission, and open a session for the shelf."""
        self.user = User.objects.create_user(username="stocktaker", password="password")
        _grant_can_inventory(self.user)
        self.client.force_login(self.user)
        self.session = InventorySession.objects.create(location=self.shelf, started_by=self.user)

    def test_set_aside_denies_without_permission(self):
        """A user lacking can_inventory is denied access to set an entry aside."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.post(reverse("curation:inventory-set-aside", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 403)

    def test_set_aside_without_pending_scan_shows_error(self):
        """Setting aside without a prior scan shows an error."""
        response = self.client.post(reverse("curation:inventory-set-aside", kwargs={"pk": self.session.pk}))

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("No pending scan to set aside.", messages)

    def test_set_aside_creates_entry_without_changing_location(self):
        """Setting a pending scan aside records it without moving the entry number."""
        self.client.post(
            reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}),
            {"entry_number": str(self.entry_number.entry_number)},
        )

        response = self.client.post(reverse("curation:inventory-set-aside", kwargs={"pk": self.session.pk}))

        self.assertRedirects(response, reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        self.entry_number.refresh_from_db()
        self.assertEqual(self.entry_number.location, self.other_shelf)
        session_entry = InventorySessionEntry.objects.get(session=self.session, entry_number=self.entry_number)
        self.assertEqual(session_entry.outcome, InventorySessionEntry.OUTCOME_SET_ASIDE)
        self.assertEqual(session_entry.previous_location, self.other_shelf)

        get_response = self.client.get(reverse("curation:inventory-scan", kwargs={"pk": self.session.pk}))
        self.assertNotContains(get_response, "Confirm this book?")


class InventorySessionCloseViewTests(TestCase):
    """Tests for the reconciliation report and closing an inventory session."""

    @classmethod
    def setUpTestData(cls):
        """Create a shelf with one confirmed, one set-aside, and one never-scanned entry number."""
        cls.building = Location.objects.create(name="Main Building", type=Location.TYPE_BUILDING)
        cls.shelf = Location.objects.create(name="Shelf 1", type=Location.TYPE_SHELF, parent=cls.building)
        cls.book = BookEntry.objects.create(title="Reconciled Book", offprint=False, has_cd=False, has_dvd=False)
        cls.confirmed_entry = EntryNumber.objects.create(entry_number=3001, book_entry=cls.book, location=cls.shelf)
        cls.set_aside_entry = EntryNumber.objects.create(entry_number=3002, book_entry=cls.book, location=cls.shelf)
        cls.missing_entry = EntryNumber.objects.create(entry_number=3003, book_entry=cls.book, location=cls.shelf)

    def setUp(self):
        """Log in a staff user with the can_inventory permission, and open a session for the shelf."""
        self.user = User.objects.create_user(username="stocktaker", password="password")
        _grant_can_inventory(self.user)
        self.client.force_login(self.user)
        self.session = InventorySession.objects.create(location=self.shelf, started_by=self.user)
        InventorySessionEntry.objects.create(
            session=self.session,
            entry_number=self.confirmed_entry,
            outcome=InventorySessionEntry.OUTCOME_CONFIRMED,
        )
        InventorySessionEntry.objects.create(
            session=self.session,
            entry_number=self.set_aside_entry,
            outcome=InventorySessionEntry.OUTCOME_SET_ASIDE,
        )

    def test_close_denies_without_permission(self):
        """A user lacking can_inventory is denied access to the close/report screen."""
        other = User.objects.create_user(username="nobody", password="password")
        self.client.force_login(other)

        response = self.client.get(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 403)

    def test_close_get_shows_reconciliation_report(self):
        """The report distinguishes confirmed, set-aside, and missing entry numbers."""
        response = self.client.get(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["confirmed_count"], 1)
        self.assertEqual(response.context["set_aside_count"], 1)
        self.assertEqual(response.context["missing_count"], 1)
        self.assertIn(self.missing_entry, response.context["missing"])

    def test_close_post_closes_open_session(self):
        """Posting to the close view marks the session closed and redirects to the hub."""
        response = self.client.post(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        self.assertRedirects(response, reverse("curation:inventory-list"))
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_open)
        self.assertIsNotNone(self.session.closed_at)

    def test_close_post_on_already_closed_session_404s(self):
        """Closing an already-closed session again is not found."""
        self.client.post(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        response = self.client.post(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 404)

    def test_close_get_after_closed_is_read_only(self):
        """The report remains viewable, in read-only mode, after the session is closed."""
        self.client.post(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        response = self.client.get(reverse("curation:inventory-close", kwargs={"pk": self.session.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["read_only"])
