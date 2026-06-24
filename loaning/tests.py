"""Tests for loaning module."""

import datetime

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from books.models import BookEntry
from books.models import EntryNumber
from loaning.forms import LoanCheckoutForm
from loaning.models import Customer
from loaning.models import Loan


class LoaningWorkflowTests(TestCase):
    """Tests for the staff loaning workflow."""

    @classmethod
    def setUpTestData(cls):
        """Create shared catalog and customer fixtures."""
        cls.book_entry = BookEntry.objects.create(
            title="Loanable book",
            subtitle="Workflow edition",
            offprint=False,
            has_cd=False,
            has_dvd=False,
            isbn="9789600000009",
        )
        cls.entry_number = EntryNumber.objects.create(
            entry_number="EN-1",
            copies=2,
            book_entry=cls.book_entry,
        )
        cls.no_copy_entry_number = EntryNumber.objects.create(
            entry_number="EN-0",
            copies=0,
            book_entry=cls.book_entry,
        )
        cls.customer = Customer.objects.create(
            first_name="Maria",
            surname="Reader",
            id_type=Customer.ID_TYPE_ID_CARD,
            id_number="A1",
            phone_number="2100000000",
            email="maria@example.com",
        )
        cls.other_customer = Customer.objects.create(
            first_name="Nikos",
            surname="Reader",
            id_type=Customer.ID_TYPE_PASSPORT,
            id_number="B1",
            phone_number="2100000001",
            email="nikos@example.com",
        )

    def setUp(self):
        """Log in a staff user with circulation permissions."""
        self.user = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_loan"),
            Permission.objects.get(codename="add_loan"),
            Permission.objects.get(codename="change_loan"),
            Permission.objects.get(codename="view_customer"),
            Permission.objects.get(codename="add_customer"),
            Permission.objects.get(codename="change_customer"),
            Permission.objects.get(codename="delete_customer"),
        )
        self.client.force_login(self.user)

    def test_checkout_form_blocks_entry_number_without_copies(self):
        """Entry numbers with zero copies cannot be loaned."""
        form = LoanCheckoutForm(
            data={
                "customer_id": self.customer.pk,
                "entry_number_id": self.no_copy_entry_number.pk,
                "start": "2026-06-17",
                "expected_end": "2026-07-01",
                "note": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("entry_number_id", form.errors)

    def test_checkout_creates_active_loan(self):
        """The loan desk creates an active loan for a selected customer and entry number."""
        response = self.client.post(
            reverse("loaning:loan-desk"),
            {
                "action": "checkout",
                "customer_id": self.customer.pk,
                "entry_number_id": self.entry_number.pk,
                "start": "2026-06-17",
                "expected_end": "2026-07-01",
                "note": "desk checkout",
            },
        )

        loan = Loan.objects.get(customer=self.customer, entry_number=self.entry_number)
        self.assertRedirects(response, reverse("loaning:loan-detail", kwargs={"pk": loan.pk}))
        self.assertEqual(loan.status, Loan.STATUS_ACTIVE)
        self.assertIsNone(loan.end)

    def test_duplicate_customer_entry_active_loan_is_allowed_with_warning(self):
        """Duplicate active loans for the same customer and entry number are allowed but warned."""
        Loan.objects.create(
            customer=self.customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 1),
            expected_end=datetime.date(2026, 6, 15),
        )

        response = self.client.post(
            reverse("loaning:loan-desk"),
            {
                "action": "checkout",
                "customer_id": self.customer.pk,
                "entry_number_id": self.entry_number.pk,
                "start": "2026-06-17",
                "expected_end": "2026-07-01",
                "note": "",
            },
        )

        self.assertEqual(
            Loan.objects.filter(
                customer=self.customer, entry_number=self.entry_number, status=Loan.STATUS_ACTIVE
            ).count(),
            2,
        )
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("This customer already has an active loan for this entry number.", messages)

    def test_checkout_blocks_when_no_available_copies_remain(self):
        """Checkout is blocked when active loans equal the copy count."""
        Loan.objects.create(
            customer=self.customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 1),
            expected_end=datetime.date(2026, 6, 15),
        )
        Loan.objects.create(
            customer=self.other_customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 2),
            expected_end=datetime.date(2026, 6, 16),
        )

        response = self.client.post(
            reverse("loaning:loan-desk"),
            {
                "action": "checkout",
                "customer_id": self.customer.pk,
                "entry_number_id": self.entry_number.pk,
                "start": "2026-06-17",
                "expected_end": "2026-07-01",
                "note": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No copies are available for loan.")

    def test_return_marks_active_loan_returned(self):
        """Returning from the loan desk closes the active loan."""
        loan = Loan.objects.create(
            customer=self.customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 1),
            expected_end=datetime.date(2026, 6, 15),
        )

        response = self.client.post(
            reverse("loaning:loan-desk"),
            {
                "action": "return",
                "loan_id": loan.pk,
                "end": "2026-06-17",
                "note": "returned",
            },
        )

        loan.refresh_from_db()
        self.assertRedirects(response, reverse("loaning:loan-desk"))
        self.assertEqual(loan.status, Loan.STATUS_RETURNED)
        self.assertEqual(loan.end, datetime.date(2026, 6, 17))
        self.assertEqual(loan.note, "returned")

    def test_mark_lost_requires_entry_number_permission_and_reduces_copies(self):
        """Marking a loan lost requires inventory permission and decrements copies."""
        loan = Loan.objects.create(
            customer=self.customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 1),
            expected_end=datetime.date(2026, 6, 15),
        )
        response = self.client.post(
            reverse("loaning:loan-detail", kwargs={"pk": loan.pk}),
            {
                "action": "lost",
                "end": "2026-06-17",
                "note": "lost copy",
            },
        )
        self.assertEqual(response.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="change_entrynumber"))
        response = self.client.post(
            reverse("loaning:loan-detail", kwargs={"pk": loan.pk}),
            {
                "action": "lost",
                "end": "2026-06-17",
                "note": "lost copy",
            },
        )

        loan.refresh_from_db()
        self.entry_number.refresh_from_db()
        self.assertRedirects(response, reverse("loaning:loan-detail", kwargs={"pk": loan.pk}))
        self.assertEqual(loan.status, Loan.STATUS_LOST)
        self.assertEqual(self.entry_number.copies, 1)

    def test_customer_delete_blocks_active_loans_and_anonymizes_closed_loans(self):
        """Customer deletion preserves history by anonymizing closed loans only."""
        active_loan = Loan.objects.create(
            customer=self.customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_ACTIVE,
            start=datetime.date(2026, 6, 1),
            expected_end=datetime.date(2026, 6, 15),
        )
        closed_loan = Loan.objects.create(
            customer=self.customer,
            entry_number=self.entry_number,
            status=Loan.STATUS_RETURNED,
            start=datetime.date(2026, 5, 1),
            expected_end=datetime.date(2026, 5, 15),
            end=datetime.date(2026, 5, 10),
        )

        response = self.client.post(reverse("loaning:customer-delete", kwargs={"pk": self.customer.pk}))
        self.assertRedirects(response, reverse("loaning:customer-edit", kwargs={"pk": self.customer.pk}))
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

        active_loan.status = Loan.STATUS_RETURNED
        active_loan.end = datetime.date(2026, 6, 10)
        active_loan.save(update_fields=["status", "end"])
        response = self.client.post(reverse("loaning:customer-delete", kwargs={"pk": self.customer.pk}))

        self.assertRedirects(response, reverse("loaning:customer-list"))
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())
        active_loan.refresh_from_db()
        closed_loan.refresh_from_db()
        self.assertIsNone(active_loan.customer)
        self.assertIsNone(closed_loan.customer)

    def test_loan_desk_search_renders_customer_and_entry_number_results(self):
        """The loan desk searches both customers and entry numbers."""
        response = self.client.get(
            reverse("loaning:loan-desk"),
            {
                "customer_q": "Maria",
                "book_q": "Loanable",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reader, Maria")
        self.assertContains(response, "EN-1")
