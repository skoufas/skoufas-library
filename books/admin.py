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

    pass


@admin.register(DbfEntry)
class DbfEntryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for DbfEntry."""

    inlines = [
        DbfEntryRowInline,
    ]


class EntryNumberInline(admin.StackedInline):
    """Customisation for EntryNumber."""

    model = EntryNumber


@admin.register(EntryNumber)
class EntryNumberAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for EntryNumber."""

    pass


@admin.register(BookEntry)
class BookEntryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for BookEntry."""

    inlines = [
        EntryNumberInline,
    ]


@admin.register(Author)
class AuthorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Author."""

    pass


@admin.register(Curator)
class CuratorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Curator."""

    pass


@admin.register(Donor)
class DonorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Donor."""

    pass


@admin.register(Translator)
class TranslatorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Translator."""

    pass


@admin.register(Editor)
class EditorAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Editor."""

    pass


@admin.register(Topic)
class Topicdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Topic."""

    pass
