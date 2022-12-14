"""Views on Books."""
from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from books.models import BookEntry
from books.models import EntryNumber


class BookEntryListView(ListView):
    """View All books."""

    model = BookEntry
    paginate_by = 100

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class BookEntryDetailView(DetailView):
    """View Book details."""

    model = BookEntry

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class BookEntryByEntryNumberDetailView(DetailView):
    """View Book details."""

    model = EntryNumber

    def get_template_names(self):
        """Reuse an existing template."""
        return ["books/bookentry_detail.html"]

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        entry_number = context["object"]
        context["entry_number"] = entry_number
        context["object"] = entry_number.book_entry
        return context
