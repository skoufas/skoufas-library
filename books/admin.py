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


@admin.register(DbfEntry)
class DbfEntryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for DbfEntry."""

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

    autocomplete_fields = [
        "entry_number_donors",
        "book_entry",
    ]


@admin.register(BookEntry)
class BookEntryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for BookEntry."""

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

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Curator)
class CuratorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Curator."""

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Donor)
class DonorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Donor."""

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Translator)
class TranslatorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Translator."""

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
    ]


@admin.register(Editor)
class EditorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Editor."""

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
