"""Views for browsing authors and donors."""

from django.db.models import Count
from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from books.models import Author, Donor


class AuthorListView(ListView):
    """View All authors."""

    model = Author
    paginate_by = 100
    ordering = ["organisation_name", "surname", "middle_name", "first_name"]

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
    ordering = ["-book_donation_count", "organisation_name", "surname", "middle_name", "first_name"]

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
