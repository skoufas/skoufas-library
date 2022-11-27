"""Models for library customers and loans"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext

from books.models import EntryNumber


class Customer(models.Model):
    """Πελάτης"""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    id_number = models.CharField(verbose_name=_("id number"), max_length=200)
    id_type = models.CharField(verbose_name=_("id type"), max_length=200)
    phone_number = models.CharField(verbose_name=_("phone number"), max_length=200)
    email = models.CharField(verbose_name=_("email"), max_length=200)
    address = models.CharField(verbose_name=_("address"), max_length=200)

    def __str__(self):
        if self.middle_name:
            return f"{self.surname}, {self.first_name} {self.middle_name}"
        else:
            return f"{self.surname}, {self.first_name}"

    class Meta:
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
    """Δανεισμός"""

    # Για 2 χρόνια, παραμένει ο δανειζόμενος
    # Μετά τα 2 χρόνια, γίνεται ανώνυμος
    customer = models.ForeignKey(Customer, verbose_name=_("customer"), null=True, on_delete=models.CASCADE)

    entry_number = models.ForeignKey(EntryNumber, verbose_name=_("Entry number"), null=True, on_delete=models.CASCADE)
    start = models.CharField(verbose_name=_("start"), max_length=4096)
    expected_end = models.CharField(verbose_name=_("expected end"), max_length=4096)
    end = models.CharField(verbose_name=_("end"), null=True, max_length=4096)
    note = models.CharField(verbose_name=_("note"), blank=True, max_length=4096)

    def __str__(self):
        return "%(customer)s / %(start)s - %(expected)s - %(end)s / %(entry)s" % {
            "customer": self.customer if self.customer else gettext("No customer"),
            "start": self.start,
            "expected": self.expected_end,
            "end": self.end if self.end else gettext("No end"),
            "entry": self.entry_number,
        }

    class Meta:
        ordering = ["end", "expected_end", "entry_number", "customer"]
        verbose_name = _("Loan")
        verbose_name_plural = _("Loans")
        constraints = [
            models.UniqueConstraint(
                name="unique_custome_entry_number_start",
                fields=["customer", "entry_number", "start"],
            ),
        ]
