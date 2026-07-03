"""Models for book entries and directly related data."""

import datetime
from typing import Any
from typing import Optional

from django.contrib.postgres.indexes import GistIndex
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.functional import Promise as StrPromise
from django.utils.text import format_lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

from books import romanize
from books.fields import EANField
from books.fields import ISBNField
from books.fields import ISSNField
from books.fields import LanguageField
from books.fields import SkoufasClassificationField
from books.skoufas_classification_classes import classification


def current_year() -> int:
    """Get the current year."""
    return datetime.date.today().year


def max_value_current_year(value: Any):
    """Check that the value is at most the current year."""
    return MaxValueValidator(current_year())(value)


class Author(models.Model):
    """Συγγραφέας."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True, blank=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True, blank=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True, blank=True)
    pseudonym = models.CharField(verbose_name=_("pseudonym"), max_length=200, null=True, blank=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True, blank=True)
    romanized_name = models.CharField(verbose_name=_("romanized name"), max_length=1000, blank=True, default="")

    def save(self, *args, **kwargs):
        """Compute romanized_name before saving."""
        parts = [self.surname, self.first_name, self.middle_name, self.pseudonym, self.organisation_name]
        combined = " ".join(p for p in parts if p)
        self.romanized_name = romanize(combined)
        super().save(*args, **kwargs)

    def __str__(self):
        """Print author."""
        parts = []
        if self.surname:
            parts.append(self.surname)
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        if not parts and self.organisation_name:
            return str(self.organisation_name)
        elif not parts and self.pseudonym:
            return str(self.pseudonym)
        elif not parts:
            return gettext("Nameless author")
        ret = ", ".join(parts)
        if self.pseudonym:
            ret = f"{ret} ({self.pseudonym})"
        return ret

    def get_absolute_url(self):
        """URL to author."""
        return reverse("books:author-by-id", kwargs={"pk": self.pk})

    class Meta:
        """Meta for author."""

        ordering = ["organisation_name", "surname", "middle_name", "first_name", "pseudonym"]
        verbose_name = _("Author")
        verbose_name_plural = _("Authors")
        indexes = [
            GistIndex(
                fields=["romanized_name"],
                name="author_romanized_name_gist",
                opclasses=["gist_trgm_ops"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_author",
                fields=["organisation_name", "surname", "middle_name", "first_name", "pseudonym"],
            )
        ]


class Translator(models.Model):
    """Μεταφραστής."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True, blank=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True, blank=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True, blank=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True, blank=True)
    romanized_name = models.CharField(verbose_name=_("romanized name"), max_length=1000, blank=True, default="")

    def save(self, *args, **kwargs):
        """Compute romanized_name before saving."""
        parts = [self.surname, self.first_name, self.middle_name, self.organisation_name]
        combined = " ".join(p for p in parts if p)
        self.romanized_name = romanize(combined)
        super().save(*args, **kwargs)

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
        indexes = [
            GistIndex(
                fields=["romanized_name"],
                name="translator_romanized_name_gist",
                opclasses=["gist_trgm_ops"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_translator",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Curator(models.Model):
    """Επιμελητής."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True, blank=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True, blank=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True, blank=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True, blank=True)
    romanized_name = models.CharField(verbose_name=_("romanized name"), max_length=1000, blank=True, default="")

    def save(self, *args, **kwargs):
        """Compute romanized_name before saving."""
        parts = [self.surname, self.first_name, self.middle_name, self.organisation_name]
        combined = " ".join(p for p in parts if p)
        self.romanized_name = romanize(combined)
        super().save(*args, **kwargs)

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
        indexes = [
            GistIndex(
                fields=["romanized_name"],
                name="curator_romanized_name_gist",
                opclasses=["gist_trgm_ops"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_curator",
                fields=["organisation_name", "surname", "middle_name", "first_name"],
            )
        ]


class Donor(models.Model):
    """Δωρητής."""

    first_name = models.CharField(verbose_name=_("first name"), max_length=200, null=True, blank=True)
    middle_name = models.CharField(verbose_name=_("middle name"), max_length=200, null=True, blank=True)
    surname = models.CharField(verbose_name=_("surname"), max_length=200, null=True, blank=True)
    organisation_name = models.CharField(verbose_name=_("organisation name"), max_length=200, null=True, blank=True)

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

    name = models.CharField(verbose_name=_("Editor"), max_length=200, null=True, blank=True)
    place = models.CharField(verbose_name=_("Editor place"), max_length=200, null=True, blank=True)
    romanized_name = models.CharField(verbose_name=_("romanized name"), max_length=1000, blank=True, default="")

    def save(self, *args, **kwargs):
        """Compute romanized_name before saving."""
        parts = [self.name, self.place]
        combined = " ".join(p for p in parts if p)
        self.romanized_name = romanize(combined)
        super().save(*args, **kwargs)

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
        indexes = [
            GistIndex(
                fields=["romanized_name"],
                name="editor_romanized_name_gist",
                opclasses=["gist_trgm_ops"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_editor",
                fields=["name", "place"],
            )
        ]


class Topic(models.Model):
    """Θέμα."""

    topic_name = models.CharField(verbose_name=_("topic"), max_length=200)
    romanized_topic_name = models.CharField(
        verbose_name=_("romanized topic name"), max_length=1000, blank=True, default=""
    )

    def save(self, *args, **kwargs):
        """Compute romanized_topic_name before saving."""
        self.romanized_topic_name = romanize(self.topic_name) if self.topic_name else ""
        super().save(*args, **kwargs)

    def __str__(self):
        """Print Topic."""
        return str(self.topic_name)

    class Meta:
        """Meta for Topic."""

        ordering = ["topic_name"]
        verbose_name = _("Topic")
        verbose_name_plural = _("Topics")
        indexes = [
            GistIndex(
                fields=["romanized_topic_name"],
                name="topic_romanized_name_gist",
                opclasses=["gist_trgm_ops"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_topic_name",
                fields=["topic_name"],
            )
        ]


class BookEntry(models.Model):
    """Καρτέλα Βιβλίου."""

    # - Title - Τίτλος
    title = models.CharField(verbose_name=_("Title"), max_length=4096, null=True, blank=False)

    # - Subtitle - Υπότιτλος
    subtitle = models.CharField(verbose_name=_("Subtitle"), max_length=4096, null=True, blank=True)

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
    editor = models.ForeignKey(Editor, verbose_name=_("editor"), null=True, on_delete=models.CASCADE, blank=True)

    # - SkoufasClassification - Ταξινομικός Αριθμός
    skoufas_classification = SkoufasClassificationField(
        verbose_name=_("Skoufas Classification"), max_length=15, null=True, blank=True
    )

    # - Language - Γλώσσα
    language = LanguageField(verbose_name=_("Language"), null=True, blank=True)

    # - Edition - Έκδοση
    edition = models.CharField(verbose_name=_("Edition"), max_length=60, null=True, blank=True)

    # - EditionDate - Έτος Έκδοσης
    edition_year = models.IntegerField(
        verbose_name=_("Edition Year"),
        validators=[MinValueValidator(1200), max_value_current_year],
        null=True,
        blank=True,
    )

    # - Pages - Σελίδες Αριθμητικά
    pages = models.IntegerField(verbose_name=_("Pages"), null=True, blank=True)

    # - Copies - Αντίτυπα Αριθμητικά
    copies = models.IntegerField(verbose_name=_("Copies"), null=True, blank=True)

    # - Volumes - Τόμοι/Τεύχη
    volumes = models.CharField(verbose_name=_("Volumes"), max_length=200, null=True, blank=True)

    # - Notes - Σημειώσεις
    notes = models.CharField(verbose_name=_("Notes"), max_length=4096, null=True, blank=True)

    # - Material - Υλικό
    material = models.CharField(verbose_name=_("Material"), max_length=4096, null=True, blank=True)

    # - ISBN
    isbn = ISBNField(null=True, blank=True)

    # - ISSN
    issn = ISSNField(null=True, blank=True)

    # - EAN
    ean = EANField(null=True, blank=True)

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

    # Donors (Many-to-Many)
    entry_donors = models.ManyToManyField(verbose_name=_("Donor"), to=Donor, blank=True)

    # Not editable, see save method
    classification_class = models.IntegerField(
        verbose_name=_("Skoufas Classification Class"), null=True, blank=True, editable=False
    )
    romanized_title = models.CharField(verbose_name=_("romanized title"), max_length=8192, blank=True, default="")

    def save(self, *args, **kwargs):
        """Update classification_class and romanized_title before saving."""
        if self.skoufas_classification:
            self.classification_class = int(self.skoufas_classification[0:3])
        else:
            self.classification_class = None
        parts = [self.title, self.subtitle]
        self.romanized_title = romanize(" ".join(p for p in parts if p))
        super().save(*args, **kwargs)

    def __str__(self):
        """Print Book entry's Title."""
        if not self.title and not self.subtitle:
            return gettext("Book with no title and subtitle")
        if not self.title:
            return str(self.subtitle)
        if not self.subtitle:
            return str(self.title)
        return f"{self.title} - {self.subtitle}"

    def get_absolute_url(self):
        """URL to book."""
        return reverse("books:book-by-id", kwargs={"pk": self.pk})

    def dbf_sequence(self) -> Optional[int]:
        """Numeric sequence in the original DBF file, if present."""
        sequence_objects = DbfEntry.objects.filter(book_entry=self)
        if sequence_objects.count() == 0:
            return None
        return sequence_objects.all()[0:1].get().dbf_sequence

    def classification_class_str(self) -> Optional[str] | StrPromise:
        """Full text of classification."""
        return classification(self.classification_class)

    class Meta:
        """Meta for Book Entry."""

        ordering = ["title", "subtitle"]
        verbose_name = _("Book Entry")
        verbose_name_plural = _("Book Entries")
        indexes = [
            GistIndex(
                fields=["romanized_title"],
                name="bookentry_romtitle_gist",
                opclasses=["gist_trgm_ops"],
            ),
        ]


class Location(models.Model):
    """Τοποθεσία."""

    TYPE_BUILDING = "building"
    TYPE_ROOM = "room"
    TYPE_SHELF = "shelf"
    TYPE_BOX = "box"
    TYPE_CHOICES = [
        (TYPE_BUILDING, _("Building")),
        (TYPE_ROOM, _("Room")),
        (TYPE_SHELF, _("Shelf")),
        (TYPE_BOX, _("Box")),
    ]

    name = models.CharField(verbose_name=_("name"), max_length=200)
    parent = models.ForeignKey(
        "self",
        verbose_name=_("parent"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    type = models.CharField(verbose_name=_("type"), max_length=20, choices=TYPE_CHOICES)
    notes = models.TextField(verbose_name=_("notes"), null=True, blank=True)
    non_public = models.BooleanField(verbose_name=_("non-public"), default=False)

    def clean(self):
        """Validate: only buildings can have a null parent."""
        if self.type != self.TYPE_BUILDING and self.parent is None:
            raise ValidationError(_("Only buildings can have no parent location."))

    def full_path(self) -> str:
        """Return the full hierarchical path, e.g. 'Building > Room > Shelf'."""
        parts = [self.name]
        node = self
        while node.parent_id is not None:
            node = node.parent
            parts.append(node.name)
        return " > ".join(reversed(parts))

    def __str__(self):
        """Return full path."""
        return self.full_path()

    def is_accessible(self, user) -> bool:
        """Return True if this location is accessible to the given user.

        Non-public nodes (and nodes with a non-public ancestor) are only
        accessible to users with the books.view_nonpublic_location permission.
        """
        if user.has_perm("books.view_nonpublic_location"):
            return True
        node: Optional["Location"] = self
        while node is not None:
            if node.non_public:
                return False
            node = node.parent if node.parent_id else None
        return True

    def get_descendant_ids(self) -> list[int]:
        """Return a list of PKs of all descendants (children, grandchildren, …)."""
        result: list[int] = []
        queue = list(self.children.values_list("pk", flat=True))
        while queue:
            pk = queue.pop()
            result.append(pk)
            queue.extend(Location.objects.filter(parent_id=pk).values_list("pk", flat=True))
        return result

    def get_absolute_url(self):
        """URL to location detail."""
        return reverse("books:location-by-id", kwargs={"pk": self.pk})

    class Meta:
        """Meta for Location."""

        ordering = ["name"]
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        permissions = [
            ("view_nonpublic_location", "Can view non-public locations"),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_location_name_per_parent",
                fields=["name", "parent"],
                nulls_distinct=False,
            )
        ]


class EntryNumber(models.Model):
    """Αριθμός Εισαγωγής."""

    entry_number = models.IntegerField(verbose_name=_("Entry number"))

    copies = models.IntegerField(verbose_name=_("Copies"), default=1, null=True, blank=True)

    book_entry = models.ForeignKey(BookEntry, verbose_name=_("Book Entry"), on_delete=models.CASCADE)

    # Donors (Many-to-Many)
    entry_number_donors = models.ManyToManyField(
        Donor,
        verbose_name=_("Donor"),
        blank=True,
    )

    location = models.ForeignKey(
        Location,
        verbose_name=_("Location"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    def __str__(self):
        """Print Book entry number, plus the entry title."""
        if self.book_entry:
            return f"{self.entry_number}: {self.book_entry}"
        else:
            return f"{self.entry_number}"

    def get_absolute_url(self):
        """URL to book entry."""
        return reverse("books:book-by-entry-number", kwargs={"pk": self.pk})

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

        ordering = ["dbfentry", "code"]

        verbose_name = _("DBF row")
        verbose_name_plural = _("DBF rows")
        constraints = [
            models.UniqueConstraint(
                fields=["dbfentry", "code"],
                name="unique_dbf_entry_row_code",
            )
        ]


def _book_entry_image_upload_to(instance: "BookEntryImage", filename: str) -> str:
    """Upload path: book_images/<book_entry_pk>/<filename>."""
    return f"book_images/{instance.book_entry_id}/{filename}"


class BookEntryImage(models.Model):
    """Φωτογραφία βιβλίου."""

    class ImageType(models.TextChoices):
        COVER = "cover", _("Cover")
        BACK_COVER = "back_cover", _("Back cover")
        INTERNAL = "internal", _("Internal page")
        OTHER = "other", _("Other")

    book_entry = models.ForeignKey(
        BookEntry,
        verbose_name=_("Book entry"),
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        verbose_name=_("Image"),
        upload_to=_book_entry_image_upload_to,
    )
    image_type = models.CharField(
        verbose_name=_("Image type"),
        max_length=20,
        choices=ImageType.choices,
        default=ImageType.COVER,
    )
    caption = models.CharField(
        verbose_name=_("Caption"),
        max_length=500,
        blank=True,
        default="",
    )
    order = models.IntegerField(
        verbose_name=_("Order"),
        default=0,
    )

    thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFit(200, 267)],
        format="JPEG",
        options={"quality": 75},
    )
    display = ImageSpecField(
        source="image",
        processors=[ResizeToFit(800, 1067)],
        format="JPEG",
        options={"quality": 85},
    )

    def __str__(self) -> str:
        """Print image type and book entry."""
        return f"{self.book_entry} - {self.get_image_type_display()}"

    class Meta:
        """Meta for BookEntryImage."""

        ordering = ["order", "pk"]
        verbose_name = _("Book Entry Image")
        verbose_name_plural = _("Book Entry Images")


@receiver(post_delete, sender=BookEntryImage)
def _delete_book_entry_image_file(sender, instance: BookEntryImage, **kwargs) -> None:
    """Delete the image file from disk when the model instance is deleted."""
    if instance.image:
        instance.image.delete(save=False)
