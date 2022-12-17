"""Book admin section customisation."""
from django.contrib import admin

from . import models

admin.site.register(models.Author)
admin.site.register(models.EntryNumber)
admin.site.register(models.BookEntry)
admin.site.register(models.Curator)
admin.site.register(models.Donor)
admin.site.register(models.Editor)
admin.site.register(models.Translator)
admin.site.register(models.Topic)


class DbfEntryRowInline(admin.TabularInline):
    """Customisation for DbfEntryRow."""

    model = models.DbfEntryRow


class DbfEntryAdmin(admin.ModelAdmin):
    """Customisation for DbfEntry."""

    inlines = [
        DbfEntryRowInline,
    ]


admin.site.register(models.DbfEntry, DbfEntryAdmin)
admin.site.register(models.DbfEntryRow)
