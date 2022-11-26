"""Models for book entries and directly related data"""
import datetime
from typing import Any
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from books.fields import ISBNField, ISSNField, EANField


def current_year() -> int:
    return datetime.date.today().year


def max_value_current_year(value: Any):
    return MaxValueValidator(current_year())(value)


class Author(models.Model):
    """Συγγραφέας"""

    first_name = models.CharField(max_length=200, null=True)
    middle_name = models.CharField(max_length=200, null=True)
    surname = models.CharField(max_length=200, null=True)
    organisation_name = models.CharField(max_length=200, null=True)

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = "Author"
        verbose_name_plural = "Authors"
        constraints = [
            models.UniqueConstraint(
                name="unique_author",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Translator(models.Model):
    """Μεταφραστής"""

    first_name = models.CharField(max_length=200, null=True)
    middle_name = models.CharField(max_length=200, null=True)
    surname = models.CharField(max_length=200, null=True)
    organisation_name = models.CharField(max_length=200, null=True)

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = "Translator"
        verbose_name_plural = "Translators"
        constraints = [
            models.UniqueConstraint(
                name="unique_translator",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Curator(models.Model):
    """Επιμελητής"""

    first_name = models.CharField(max_length=200, null=True)
    middle_name = models.CharField(max_length=200, null=True)
    surname = models.CharField(max_length=200, null=True)
    organisation_name = models.CharField(max_length=200, null=True)

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = "Curator"
        verbose_name_plural = "Curators"
        constraints = [
            models.UniqueConstraint(
                name="unique_curator",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Donor(models.Model):
    """Δωρητής"""

    first_name = models.CharField(max_length=200, null=True)
    middle_name = models.CharField(max_length=200, null=True)
    surname = models.CharField(max_length=200, null=True)
    organisation_name = models.CharField(max_length=200, null=True)

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = "Donor"
        verbose_name_plural = "Donors"
        constraints = [
            models.UniqueConstraint(
                name="unique_donor",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Editor(models.Model):
    """Εκδότης"""

    name = models.CharField(max_length=200, null=True)
    place = models.CharField(max_length=200, null=True)

    class Meta:
        ordering = ["name", "place"]
        verbose_name = "Editor"
        verbose_name_plural = "Editors"
        constraints = [
            models.UniqueConstraint(
                name="unique_editor",
                fields=["name", "place"],
            )
        ]


class Topic(models.Model):
    """Θέμα"""

    topic_name = models.CharField(max_length=200)

    class Meta:
        ordering = ["topic_name"]
        verbose_name = "Topic"
        verbose_name_plural = "Topics"
        constraints = [
            models.UniqueConstraint(
                name="unique_topic_name",
                fields=["topic_name"],
            )
        ]


class BookEntry(models.Model):
    """Καρτέλα Βιβλίου"""

    # ### Authorship (Many-to-Many)
    authors = models.ManyToManyField(to=Author)

    # ### Translation (Many-to-Many)
    translators = models.ManyToManyField(Translator)

    # ### Curation (Many-to-Many)
    curators = models.ManyToManyField(Curator)

    # ### Topics (Many-to-Many)
    topics = models.ManyToManyField(Topic)

    # - EditorId (FK: Editor)
    editor = models.ForeignKey(Editor, null=True, on_delete=models.CASCADE)

    # - Title - Τίτλος
    title = models.CharField(max_length=4096, null=True)

    # - Subtitle - Υπότιτλος
    subtitle = models.CharField(max_length=4096, null=True)

    # - Dewey - Ταξινομικός Αριθμός Dewey
    dewey = models.CharField(max_length=15, null=True)

    # - Language - Γλώσσα
    language = models.CharField(max_length=8, null=True)

    # - Edition - Έκδοση
    edition = models.CharField(max_length=60, null=True)

    # - EditionDate - Έτος Έκδοσης
    edition_year = models.IntegerField(
        validators=[MinValueValidator(1200), max_value_current_year], null=True
    )

    # - Pages - Σελίδες Αριθμητικά
    pages = models.IntegerField(null=True)

    # - Copies - Αντίτυπα Αριθμητικά
    copies = models.IntegerField(null=True)

    # Donors (Many-to-Many)
    donors = models.ManyToManyField(Donor)

    # - Volumes - Τόμοι/Τεύχη
    volumes = models.CharField(max_length=100, null=True)

    # - Notes - Σημειώσεις
    notes = models.CharField(max_length=4096, null=True)

    # - Material - Υλικό
    material = models.CharField(max_length=4096, null=True)

    # - ISBN
    isbn = ISBNField(null=True)

    # - ISSN
    issn = ISSNField(null=True)

    # - EAN
    ean = EANField(null=True)

    # - Offprint - ΑΝΑΤΥΠΟ
    offprint = models.BooleanField()

    # - HasCD - Έχει
    has_cd = models.BooleanField()

    # - HasDVD - Έχει
    has_dvd = models.BooleanField()

    class Meta:
        ordering = ["title", "subtitle"]
        verbose_name = "Book Entry"
        verbose_name_plural = "Book Entries"


class EntryNumber(models.Model):
    """Αριθμός Εισαγωγής"""

    entry_number = models.CharField(max_length=200)

    copies = models.IntegerField(default=0, null=True)

    book_entry = models.ForeignKey(BookEntry, on_delete=models.CASCADE)

    # Donors (Many-to-Many)
    donors = models.ManyToManyField(Donor)

    class Meta:
        ordering = ["entry_number"]
        verbose_name = "Entry Number"
        verbose_name_plural = "Entry Numbers"
        constraints = [
            models.UniqueConstraint(
                name="unique_entry_number",
                fields=["entry_number"],
            )
        ]


class DbfEntry(models.Model):
    """Καρτέλα DBASE"""

    book_entry = models.ForeignKey(BookEntry, null=True, on_delete=models.CASCADE)
    dbf_sequence = models.IntegerField(default=0, editable=False)
    import_time = models.DateTimeField(editable=False)

    class Meta:
        ordering = ["-import_time", "dbf_sequence"]
        verbose_name = "DBF entry"
        verbose_name_plural = "DBF entries"
        unique_together = [["import_time", "dbf_sequence"]]


class DbfEntryRow(models.Model):
    """Γραμμή σε καρτέλα DBASE"""

    dbfentry = models.ForeignKey(DbfEntry, on_delete=models.CASCADE, editable=False)
    code = models.IntegerField()
    # Length obtained via
    # max([max([len(value) for value in record.values()]) for record in books_table])
    value = models.CharField(max_length=65)

    class Meta:
        order_with_respect_to = "dbfentry"
        verbose_name = "DBF row"
        verbose_name_plural = "DBF rows"
        unique_together = [["dbfentry", "code"]]
