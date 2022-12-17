"""Book management."""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BooksConfig(AppConfig):
    """Book management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "books"
    verbose_name = _("books")
