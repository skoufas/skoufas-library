"""Views for browsing books by catalogue, entry number, and classification."""

from django.db.models import Count
from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from books.models import BookEntry, EntryNumber
from books.skoufas_classification_classes import classification


class BookEntryListView(ListView):
    """View All books."""

    model = BookEntry
    paginate_by = 100

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class BookEntryByMainClassListView(BookEntryListView):
    """View books by main class."""

    def get_queryset(self):
        """Return books with a specific class number."""
        self.classification_class = self.kwargs["classification_class"]
        if self.classification_class == "None":
            self.classification_class = None
        return BookEntry.objects.filter(classification_class=self.classification_class)


class BookEntryBySkoufasClassificationListView(BookEntryListView):
    """View books by main class."""

    def get_queryset(self):
        """Return books with a specific classification string."""
        self.skoufas_classification = self.kwargs["skoufas_classification"]
        if self.skoufas_classification == "None":
            self.skoufas_classification = None
        return BookEntry.objects.filter(skoufas_classification=self.skoufas_classification)


class BookEntryDetailView(DetailView):
    """View Book details."""

    model = BookEntry

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        user = self.request.user
        entry_numbers = list(context["object"].entrynumber_set.all())
        for en in entry_numbers:
            en.location_accessible = en.location.is_accessible(user) if en.location else False
        context["entry_numbers"] = entry_numbers
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
        book_entry = entry_number.book_entry
        context["object"] = book_entry
        user = self.request.user
        entry_numbers = list(book_entry.entrynumber_set.all())
        for en in entry_numbers:
            en.location_accessible = en.location.is_accessible(user) if en.location else False
        context["entry_numbers"] = entry_numbers
        return context


class ClassListView(ListView):
    """View All classes."""

    model = BookEntry

    def get_template_names(self):
        """Reuse an existing template."""
        return ["books/class_list.html"]

    def get_context_data(self, **kwargs):
        """Add details."""
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()

        it = (
            BookEntry.objects.order_by("classification_class", "skoufas_classification")
            .values("classification_class", "skoufas_classification")
            .annotate(number_of_entries=Count("skoufas_classification"))
        )
        classes = []
        current_class = "foo"
        current_subclasses = []
        for r in it:
            if r["classification_class"] != current_class:
                if current_class != "foo":
                    classes.append(
                        {
                            "classification_class": current_class,
                            "description": classification(current_class),
                            "subclasses": current_subclasses,
                            "number_of_entries": sum([e["number_of_entries"] for e in current_subclasses]),
                        }
                    )
                    current_subclasses = []
            current_class = r["classification_class"]
            current_subclasses.append(r)
        classes.append(
            {
                "classification_class": current_class,
                "description": classification(current_class),
                "subclasses": current_subclasses,
                "number_of_entries": sum([e["number_of_entries"] for e in current_subclasses]),
            }
        )
        context["classes"] = classes
        return context
