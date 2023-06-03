"""Views on Books."""
from django.db.models import Count
from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from books.models import Author
from books.models import BookEntry
from books.models import Donor
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


class AuthorListView(ListView):
    """View All authors."""

    model = Author
    paginate_by = 100

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class AuthorDetailView(DetailView):
    """View Author details."""

    model = Author

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class DonorListView(ListView):
    """View All donors."""

    model = Donor
    paginate_by = 100
    queryset = Donor.objects.annotate(book_donation_count=Count("bookentry"))
    ordering = ["-book_donation_count"]

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class DonorDetailView(DetailView):
    """View Author details."""

    model = Donor

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context
