"""Models for library customers and loans."""

import datetime

from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from books.models import EntryNumber


class Customer(models.Model):
    """Πελάτης."""

    ID_TYPE_ID_CARD = "id_card"
    ID_TYPE_PASSPORT = "passport"
    ID_TYPE_DRIVER_LICENSE = "driver_license"
    ID_TYPE_OTHER = "other"
    ID_TYPE_CHOICES = [
        (ID_TYPE_ID_CARD, _("ID Card")),
        (ID_TYPE_PASSPORT, _("Passport")),
        (ID_TYPE_DRIVER_LICENSE, _("Driver's License")),
        (ID_TYPE_OTHER, _("Other")),
    ]

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, blank=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True, blank=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, blank=True)
    id_number = models.CharField(verbose_name=_("id number"), max_length=200, blank=True)
    id_type = models.CharField(verbose_name=_("id type"), max_length=20, blank=True, choices=ID_TYPE_CHOICES)
    phone_number = models.CharField(verbose_name=_("phone number"), max_length=200, blank=True)
    email = models.CharField(verbose_name=_("email"), max_length=200, blank=True)
    address = models.CharField(verbose_name=_("address"), max_length=200, blank=True)
    skoufas_member_id = models.CharField(verbose_name=_("Skoufas member ID"), max_length=200, blank=True, null=True)

    def __str__(self):
        """Print customer name."""
        if self.middle_name:
            return f"{self.surname}, {self.first_name} {self.middle_name}"
        else:
            return f"{self.surname}, {self.first_name}"

    class Meta:
        """Meta for Customer."""

        ordering = ["surname", "middle_name", "first_name"]
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        constraints = [
            models.UniqueConstraint(
                name="unique_name_and_number",
                fields=["surname", "middle_name", "first_name", "phone_number"],
            ),
            models.UniqueConstraint(
                name="unique_id_document",
                fields=[
                    "id_type",
                    "id_number",
                ],
            ),
        ]


class Loan(models.Model):
    """Δανεισμός."""

    STATUS_ACTIVE = "active"
    STATUS_RETURNED = "returned"
    STATUS_LOST = "lost"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, _("Active")),
        (STATUS_RETURNED, _("Returned")),
        (STATUS_LOST, _("Lost")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    # Για 2 χρόνια, παραμένει ο δανειζόμενος
    # Μετά τα 2 χρόνια, γίνεται ανώνυμος
    customer = models.ForeignKey(Customer, verbose_name=_("customer"), null=True, on_delete=models.SET_NULL, blank=True)

    entry_number = models.ForeignKey(EntryNumber, verbose_name=_("Entry number"), on_delete=models.CASCADE)
    status = models.CharField(verbose_name=_("status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    start = models.DateField(verbose_name=_("start"))
    expected_end = models.DateField(verbose_name=_("expected end"))
    end = models.DateField(verbose_name=_("end"), null=True, blank=True)
    note = models.CharField(verbose_name=_("note"), blank=True, max_length=4096)

    @property
    def is_overdue(self):
        """Return whether this active loan is past its expected return date."""
        return self.status == self.STATUS_ACTIVE and self.expected_end < datetime.date.today()

    def __str__(self):
        """Print Loan details."""
        return "%(customer)s / %(start)s - %(expected)s - %(end)s / %(entry)s" % {
            "customer": self.customer if self.customer else gettext("No customer"),
            "start": self.start,
            "expected": self.expected_end,
            "end": self.end if self.end else gettext("No end"),
            "entry": self.entry_number,
        }

    class Meta:
        """Meta for Loan."""

        ordering = ["status", "end", "expected_end", "entry_number", "customer"]
        verbose_name = _("Loan")
        verbose_name_plural = _("Loans")
