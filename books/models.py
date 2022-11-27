"""Models for book entries and directly related data"""
import datetime
from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext

from books.fields import EANField, ISBNField, ISSNField


def current_year() -> int:
    return datetime.date.today().year


def max_value_current_year(value: Any):
    return MaxValueValidator(current_year())(value)


class Author(models.Model):
    """Συγγραφέας"""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        if self.organisation_name and str(self.organisation_name):
            return str(self.organisation_name)
        else:
            if not self.first_name and not self.surname:
                return gettext("Nameless author")
            if self.middle_name:
                return f"{self.surname}, {self.first_name} {self.middle_name}"
            else:
                return f"{self.surname}, {self.first_name}"

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = _("Author")
        verbose_name_plural = _("Authors")
        constraints = [
            models.UniqueConstraint(
                name="unique_author",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Translator(models.Model):
    """Μεταφραστής"""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        if self.organisation_name and str(self.organisation_name):
            return str(self.organisation_name)
        else:
            if not self.first_name and not self.surname:
                return gettext("Nameless translator")
            if self.middle_name:
                return f"{self.surname}, {self.first_name} {self.middle_name}"
            else:
                return f"{self.surname}, {self.first_name}"

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = _("Translator")
        verbose_name_plural = _("Translators")
        constraints = [
            models.UniqueConstraint(
                name="unique_translator",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Curator(models.Model):
    """Επιμελητής"""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        if self.organisation_name and str(self.organisation_name):
            return str(self.organisation_name)
        else:
            if not self.first_name and not self.surname:
                return gettext("Nameless curator")
            if self.middle_name:
                return f"{self.surname}, {self.first_name} {self.middle_name}"
            else:
                return f"{self.surname}, {self.first_name}"

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = _("Curator")
        verbose_name_plural = _("Curators")
        constraints = [
            models.UniqueConstraint(
                name="unique_curator",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Donor(models.Model):
    """Δωρητής"""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        if self.organisation_name and str(self.organisation_name):
            return str(self.organisation_name)
        else:
            if not self.first_name and not self.surname:
                return gettext("Nameless donor")
            if self.middle_name:
                return f"{self.surname}, {self.first_name} {self.middle_name}"
            else:
                return f"{self.surname}, {self.first_name}"

    class Meta:
        ordering = ["organisation_name", "surname", "middle_name", "first_name"]
        verbose_name = _("Donor")
        verbose_name_plural = _("Donors")
        constraints = [
            models.UniqueConstraint(
                name="unique_donor",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Editor(models.Model):
    """Εκδότης"""

    name = models.CharField(verbose_name=_("Editor"), max_length=200, null=True)
    place = models.CharField(verbose_name=_("Editor place"), max_length=200, null=True)

    def __str__(self):
        if not self.place and not self.name:
            return gettext("Nameless editor")
        if not self.place:
            return self.name
        if not self.name:
            return gettext("Unknown editor in %(place)s") % {"place": self.place}
        else:
            return f"{self.name}, {self.place}"

    class Meta:
        ordering = ["name", "place"]
        verbose_name = _("Editor")
        verbose_name_plural = _("Editors")
        constraints = [
            models.UniqueConstraint(
                name="unique_editor",
                fields=["name", "place"],
            )
        ]


class Topic(models.Model):
    """Θέμα"""

    topic_name = models.CharField(verbose_name=_("topic"), max_length=200)

    def __str__(self):
        return str(self.topic_name)

    class Meta:
        ordering = ["topic_name"]
        verbose_name = _("Topic")
        verbose_name_plural = _("Topics")
        constraints = [
            models.UniqueConstraint(
                name="unique_topic_name",
                fields=["topic_name"],
            )
        ]


class BookEntry(models.Model):
    """Καρτέλα Βιβλίου"""

    # ### Authorship (Many-to-Many)
    authors = models.ManyToManyField(
        verbose_name=_("Author"),
        to=Author,
    )

    # ### Translation (Many-to-Many)
    translators = models.ManyToManyField(verbose_name=_("Translator"), to=Translator)

    # ### Curation (Many-to-Many)
    curators = models.ManyToManyField(verbose_name=_("Curator"), to=Curator)

    # ### Topics (Many-to-Many)
    topics = models.ManyToManyField(verbose_name=_("Topic"), to=Topic)

    # - EditorId (FK: Editor)
    editor = models.ForeignKey(Editor, verbose_name=_("editor"), null=True, on_delete=models.CASCADE)

    # - Title - Τίτλος
    title = models.CharField(verbose_name=_("Title"), max_length=4096, null=True)

    # - Subtitle - Υπότιτλος
    subtitle = models.CharField(verbose_name=_("Subtitle"), max_length=4096, null=True)

    # - Dewey - Ταξινομικός Αριθμός Dewey
    dewey = models.CharField(verbose_name=_("Dewey"), max_length=15, null=True)

    # - Language - Γλώσσα
    language = models.CharField(verbose_name=_("Language"), max_length=8, null=True)

    # - Edition - Έκδοση
    edition = models.CharField(verbose_name=_("Edition"), max_length=60, null=True)

    # - EditionDate - Έτος Έκδοσης
    edition_year = models.IntegerField(
        verbose_name=_("Edition Year"), validators=[MinValueValidator(1200), max_value_current_year], null=True
    )

    # - Pages - Σελίδες Αριθμητικά
    pages = models.IntegerField(verbose_name=_("Pages"), null=True)

    # - Copies - Αντίτυπα Αριθμητικά
    copies = models.IntegerField(verbose_name=_("Copies"), null=True)

    # Donors (Many-to-Many)
    donors = models.ManyToManyField(verbose_name=_("Donor"), to=Donor)

    # - Volumes - Τόμοι/Τεύχη
    volumes = models.CharField(verbose_name=_("Volumes"), max_length=100, null=True)

    # - Notes - Σημειώσεις
    notes = models.CharField(verbose_name=_("Notes"), max_length=4096, null=True)

    # - Material - Υλικό
    material = models.CharField(verbose_name=_("Material"), max_length=4096, null=True)

    # - ISBN
    isbn = ISBNField(null=True)

    # - ISSN
    issn = ISSNField(null=True)

    # - EAN
    ean = EANField(null=True)

    # - Offprint - ΑΝΑΤΥΠΟ
    offprint = models.BooleanField(verbose_name=_("Offprint"))

    # - HasCD - Έχει
    has_cd = models.BooleanField(
        verbose_name=_("Has CD"),
    )

    # - HasDVD - Έχει
    has_dvd = models.BooleanField(
        verbose_name=_("Has DVD"),
    )

    def __str__(self):
        if not self.title and not self.subtitle:
            return gettext("Book with no title and subtitle")
        if not self.title:
            return str(self.subtitle)
        if not self.subtitle:
            return str(self.title)
        return f"{self.title} - {self.subtitle}"

    class Meta:
        ordering = ["title", "subtitle"]
        verbose_name = _("Book Entry")
        verbose_name_plural = _("Book Entries")


class EntryNumber(models.Model):
    """Αριθμός Εισαγωγής"""

    entry_number = models.CharField(verbose_name=_("Entry number"), max_length=200)

    copies = models.IntegerField(verbose_name=_("Copies"), default=0, null=True)

    book_entry = models.ForeignKey(BookEntry, verbose_name=_("Book Entry"), on_delete=models.CASCADE)

    # Donors (Many-to-Many)
    donors = models.ManyToManyField(
        Donor,
        verbose_name=_("Donor"),
    )

    def __str__(self):
        if self.book_entry:
            return f"{self.entry_number}: {self.book_entry}"
        else:
            return f"{self.entry_number}"

    class Meta:
        ordering = ["entry_number"]
        verbose_name = _("Entry Number")
        verbose_name_plural = _("Entry Numbers")
        constraints = [
            models.UniqueConstraint(
                name="unique_entry_number",
                fields=["entry_number"],
            )
        ]


class DbfEntry(models.Model):
    """Καρτέλα DBASE"""

    book_entry = models.ForeignKey(BookEntry, verbose_name=_("Book Entry"), null=True, on_delete=models.CASCADE)
    dbf_sequence = models.IntegerField(verbose_name=_("DBF Sequence"), default=0, editable=False)
    import_time = models.DateTimeField(verbose_name=_("Import Time"), editable=False)

    def __str__(self):
        if self.book_entry:
            return f"{self.dbf_sequence:05}: {self.book_entry}"
        else:
            return f"{self.dbf_sequence:05}"

    class Meta:
        ordering = ["-import_time", "dbf_sequence"]
        verbose_name = _("DBF entry")
        verbose_name_plural = _("DBF entries")
        unique_together = [["import_time", "dbf_sequence"]]


class DbfEntryRow(models.Model):
    """Γραμμή σε καρτέλα DBASE"""

    dbfentry = models.ForeignKey(DbfEntry, verbose_name=_("DBF entry"), on_delete=models.CASCADE, editable=False)
    code = models.IntegerField(
        verbose_name=_("Code"),
    )
    # Length obtained via
    # max([max([len(value) for value in record.values()]) for record in books_table])
    value = models.CharField(verbose_name=_("Value"), max_length=65)

    def __str__(self):
        if self.value:
            return f"{self.dbfentry.dbf_sequence:05}/{self.code:02}: {self.value}"
        else:
            return f"{self.dbfentry.dbf_sequence:05}/{self.code:02}:"

    class Meta:
        order_with_respect_to = "dbfentry"
        verbose_name = _("DBF row")
        verbose_name_plural = _("DBF rows")
        unique_together = [["dbfentry", "code"]]
