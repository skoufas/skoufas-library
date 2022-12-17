"""Models for book entries and directly related data."""
import datetime
from typing import Any
from typing import Optional

from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from books.fields import DeweyField
from books.fields import EANField
from books.fields import ISBNField
from books.fields import ISSNField


def current_year() -> int:
    """Get the current year."""
    return datetime.date.today().year


def max_value_current_year(value: Any):
    """Check that the value is at most the current year."""
    return MaxValueValidator(current_year())(value)


class Author(models.Model):
    """Συγγραφέας."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        """Print author."""
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
        """Meta for author."""

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
    """Μεταφραστής."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        """Print Translator."""
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
        """Meta for Translator."""

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
    """Επιμελητής."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        """Print Curator."""
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
        """Meta for Curator."""

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
    """Δωρητής."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True)

    def __str__(self):
        """Print Donor."""
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
        """Meta for Donor."""

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
    """Εκδότης."""

    name = models.CharField(verbose_name=_("Editor"), max_length=200, null=True)
    place = models.CharField(verbose_name=_("Editor place"), max_length=200, null=True)

    def __str__(self):
        """Print Editor."""
        if not self.place and not self.name:
            return gettext("Nameless editor")
        if not self.place:
            return self.name
        if not self.name:
            return str(format_lazy(gettext("Unknown editor in {}"), self.place))
        else:
            return f"{self.name}, {self.place}"

    class Meta:
        """Meta for Editor."""

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
    """Θέμα."""

    topic_name = models.CharField(verbose_name=_("topic"), max_length=200)

    def __str__(self):
        """Print Topic."""
        return str(self.topic_name)

    class Meta:
        """Meta for Topic."""

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
    """Καρτέλα Βιβλίου."""

    # ### Authorship (Many-to-Many)
    authors = models.ManyToManyField(
        verbose_name=_("Author"),
        to=Author,
        blank=True,
    )

    # ### Translation (Many-to-Many)
    translators = models.ManyToManyField(verbose_name=_("Translator"), to=Translator, blank=True)

    # ### Curation (Many-to-Many)
    curators = models.ManyToManyField(verbose_name=_("Curator"), to=Curator, blank=True)

    # ### Topics (Many-to-Many)
    topics = models.ManyToManyField(verbose_name=_("Topic"), to=Topic, blank=True)

    # - EditorId (FK: Editor)
    editor = models.ForeignKey(Editor, verbose_name=_("editor"), null=True, on_delete=models.CASCADE)

    # - Title - Τίτλος
    title = models.CharField(verbose_name=_("Title"), max_length=4096, null=True)

    # - Subtitle - Υπότιτλος
    subtitle = models.CharField(verbose_name=_("Subtitle"), max_length=4096, null=True)

    # - Dewey - Ταξινομικός Αριθμός Dewey
    dewey = DeweyField(verbose_name=_("Dewey"), max_length=15, null=True)

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
    entry_donors = models.ManyToManyField(verbose_name=_("Donor"), to=Donor, blank=True)

    # - Volumes - Τόμοι/Τεύχη
    volumes = models.CharField(verbose_name=_("Volumes"), max_length=200, null=True)

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
        """Print Book entry's Title."""
        if not self.title and not self.subtitle:
            return gettext("Book with no title and subtitle")
        if not self.title:
            return str(self.subtitle)
        if not self.subtitle:
            return str(self.title)
        return f"{self.title} - {self.subtitle}"

    def dbf_sequence(self) -> Optional[int]:
        """Numeric sequence in the original DBF file, if present."""
        s = DbfEntry.objects.filter(book_entry=self)
        if s.count() == 0:
            return None
        return s.all()[0:1].get().dbf_sequence

    class Meta:
        """Meta for Book Entry."""

        ordering = ["title", "subtitle"]
        verbose_name = _("Book Entry")
        verbose_name_plural = _("Book Entries")


class EntryNumber(models.Model):
    """Αριθμός Εισαγωγής."""

    entry_number = models.CharField(verbose_name=_("Entry number"), max_length=200)

    copies = models.IntegerField(verbose_name=_("Copies"), default=0, null=True)

    book_entry = models.ForeignKey(BookEntry, verbose_name=_("Book Entry"), on_delete=models.CASCADE)

    # Donors (Many-to-Many)
    entry_number_donors = models.ManyToManyField(
        Donor,
        verbose_name=_("Donor"),
        blank=True,
    )

    def __str__(self):
        """Print Book entry number, plus the entry title."""
        if self.book_entry:
            return f"{self.entry_number}: {self.book_entry}"
        else:
            return f"{self.entry_number}"

    class Meta:
        """Meta for EntryNumber."""

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
    """Καρτέλα DBASE."""

    book_entry = models.ForeignKey(BookEntry, verbose_name=_("Book Entry"), null=True, on_delete=models.CASCADE)
    dbf_sequence = models.IntegerField(verbose_name=_("DBF Sequence"), default=0, editable=False)
    import_time = models.DateTimeField(verbose_name=_("Import Time"), editable=False)

    def __str__(self):
        """Print dbf entry number, plus the entry title."""
        if self.book_entry:
            return f"{self.dbf_sequence:05}: {self.book_entry}"
        else:
            return f"{self.dbf_sequence:05}"

    def as_yaml(self):
        """Extract a yaml-like representation."""
        return "\n".join(["---"] + [f"{row.code}: {row.value}" for row in self.dbfentryrow_set.all()])

    class Meta:
        """Meta for DbfEntry."""

        ordering = ["-import_time", "dbf_sequence"]
        verbose_name = _("DBF entry")
        verbose_name_plural = _("DBF entries")
        constraints = [
            models.UniqueConstraint(
                name="unique_dbf_sequence",
                fields=["dbf_sequence"],
            )
        ]


class DbfEntryRow(models.Model):
    """Γραμμή σε καρτέλα DBASE."""

    dbfentry = models.ForeignKey(DbfEntry, verbose_name=_("DBF entry"), on_delete=models.CASCADE, editable=False)
    code = models.IntegerField(
        verbose_name=_("Code"),
    )
    # Length obtained via
    # max([max([len(value) for value in record.values()]) for record in books_table])
    value = models.CharField(verbose_name=_("Value"), max_length=65)

    def __str__(self):
        """Print dbf row and value."""
        if self.value:
            return f"{self.dbfentry.dbf_sequence:05}/{self.code:02}: {self.value}"
        else:
            return f"{self.dbfentry.dbf_sequence:05}/{self.code:02}:"

    class Meta:
        """Meta for DbfEntryRow."""

        order_with_respect_to = "dbfentry"
        verbose_name = _("DBF row")
        verbose_name_plural = _("DBF rows")
        unique_together = [["dbfentry", "code"]]
