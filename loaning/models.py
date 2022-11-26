"""Models for library customers and loans"""
from django.db import models
from books.models import EntryNumber


class Customer(models.Model):
    """Πελάτης"""

    name = models.CharField(max_length=200)
    middle_name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    full_name = models.CharField(max_length=200)
    id_number = models.CharField(max_length=200)
    id_type = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    address = models.CharField(max_length=200)


class Loan(models.Model):
    """Δανεισμός"""

    # Για 2 χρόνια, παραμένει ο δανειζόμενος
    # Μετά τα 2 χρόνια, γίνεται ανώνυμος
    customer = models.ForeignKey(Customer, null=True, on_delete=models.CASCADE)

    entry_number = models.ForeignKey(EntryNumber, null=True, on_delete=models.CASCADE)
    start = models.CharField(max_length=4096)
    expected_end = models.CharField(max_length=4096)
    end = models.CharField(max_length=4096)
    note = models.CharField(max_length=4096)
