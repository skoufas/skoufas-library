"""Book admin section customisation."""
from django.contrib import admin
from djangoql.admin import DjangoQLSearchMixin

from .models import Author
from .models import BookEntry
from .models import Curator
from .models import DbfEntry
from .models import DbfEntryRow
from .models import Donor
from .models import Editor
from .models import EntryNumber
from .models import Topic
from .models import Translator


class DbfEntryRowInline(admin.TabularInline):
    """Customisation for DbfEntryRow."""

    model = DbfEntryRow


@admin.register(DbfEntryRow)
class DbfEntryRowAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for DbfEntryRow."""

    list_display = ["dbfentry", "code", "value"]


@admin.register(DbfEntry)
class DbfEntryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for DbfEntry."""

    list_display = ["dbf_sequence", "book_entry"]

    autocomplete_fields = [
        "book_entry",
    ]

    inlines = [
        DbfEntryRowInline,
    ]


class EntryNumberInline(admin.StackedInline):
    """Customisation for EntryNumber."""

    model = EntryNumber

    autocomplete_fields = [
        "entry_number_donors",
    ]


@admin.register(EntryNumber)
class EntryNumberAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for EntryNumber."""

    list_display = [
        "entry_number",
        "book_entry",
    ]

    autocomplete_fields = [
        "entry_number_donors",
        "book_entry",
    ]


@admin.register(BookEntry)
class BookEntryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for BookEntry."""

    list_display = [
        "title",
        "subtitle",
        "authors_list",
        "skoufas_classification",
        "language",
        "edition",
        "edition_year",
        "editor",
        "pages",
        "copies",
        "volumes",
        "isbn",
        "issn",
        "ean",
        "offprint",
        "has_cd",
        "has_dvd",
    ]

    @admin.display(description="Author")
    def authors_list(self, obj):
        """Return a non sortable display."""
        return ", ".join(str(author) for author in obj.authors.all())

    inlines = [
        EntryNumberInline,
    ]

    autocomplete_fields = ["authors", "translators", "curators", "editor", "entry_donors", "topics"]

    search_fields = [
        "title",
        "subtitle",
        "authors__organisation_name",
        "authors__surname",
        "authors__first_name",
        "authors__middle_name",
    ]


@admin.register(Author)
class AuthorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Author."""

    list_display = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Curator)
class CuratorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Curator."""

    list_display = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Donor)
class DonorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Donor."""

    list_display = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Translator)
class TranslatorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Translator."""

    list_display = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Editor)
class EditorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Editor."""

    list_display = [
        "name",
        "place",
    ]

    search_fields = [
        "name",
        "place",
    ]


@admin.register(Topic)
class Topicdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Topic."""

    search_fields = [
        "topic_name",
    ]
