"""Views on Books."""
from django.utils import timezone
from django.views.generic.detail import DetailView

from books.models import BookEntry


class BookEntryDetailView(DetailView):
    """View Book details."""

    model = BookEntry

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context
