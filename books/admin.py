"""Book admin section customisation."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from djangoql.admin import DjangoQLSearchMixin

from .models import Author
from .models import BookEntry
from .models import BookEntryImage
from .models import Curator
from .models import DbfEntry
from .models import DbfEntryRow
from .models import Donor
from .models import Editor
from .models import EntryNumber
from .models import Location
from .models import Topic
from .models import Translator


class BookEntryImageInline(admin.TabularInline):
    """Inline for BookEntryImage."""

    model = BookEntryImage
    extra = 0


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
        "location",
    ]

    def get_formset(self, request, obj=None, **kwargs):
        """Annotate entry_number with the next suggested value."""
        formset = super().get_formset(request, obj, **kwargs)
        from django.db.models import Max

        max_val = EntryNumber.objects.aggregate(Max("entry_number"))["entry_number__max"]
        next_val = (max_val or 0) + 1
        formset.form.base_fields["entry_number"].help_text = _("Next available: %(n)s") % {"n": next_val}
        return formset


@admin.register(EntryNumber)
class EntryNumberAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for EntryNumber."""

    list_display = [
        "entry_number",
        "book_entry",
        "location",
    ]

    autocomplete_fields = [
        "entry_number_donors",
        "book_entry",
        "location",
    ]

    search_fields = [
        "=entry_number",
        "book_entry__title",
        "book_entry__subtitle",
    ]

    def get_form(self, request, obj=None, **kwargs):
        """Annotate entry_number with the next suggested value when adding."""
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            from django.db.models import Max

            max_val = EntryNumber.objects.aggregate(Max("entry_number"))["entry_number__max"]
            next_val = (max_val or 0) + 1
            form.base_fields["entry_number"].help_text = _("Next available: %(n)s") % {"n": next_val}
        return form


@admin.register(Location)
class LocationAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Location."""

    list_display = [
        "name",
        "type",
        "parent",
        "non_public",
    ]

    list_filter = ["type", "non_public"]

    autocomplete_fields = ["parent"]

    search_fields = ["name"]


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
        BookEntryImageInline,
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
        "pseudonym",
    ]

    search_fields = [
        "organisation_name",
        "surname",
        "first_name",
        "middle_name",
        "pseudonym",
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
