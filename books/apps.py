"""Book management."""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from watson import search as watson_search


class BooksConfig(AppConfig):
    """Book management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "books"
    verbose_name = _("books")

    def ready(self):
        """Set up watson indices."""
        watson_search.register(self.get_model("Author"))
        watson_search.register(self.get_model("BookEntry"))
        watson_search.register(self.get_model("EntryNumber"), fields=("entry_number",))
