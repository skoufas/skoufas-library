"""Views on Books."""
import csv
from typing import Any

from django.db.models import Count
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views import View
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
        from .skoufas_classification_classes import classification

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


class CSVExportView(View):
    """A view that streams a large CSV file with all book entries."""

    class Echo:
        """An object that implements just the write method of the file-like interface."""

        def write(self, value):
            """Write the value by returning it, instead of storing in a buffer."""
            return value

    def head_csv_row(self) -> list[str]:
        """Return a list of CSV column names."""
        return [
            "entry_number",
            "title",
            "subtitle",
            "author_1",
            "author_2",
            "author_3",
            "author_4",
            "translator_1",
            "translator_2",
            "translator_3",
            "curator_1",
            "curator_2",
            "curator_3",
            "topic_1",
            "topic_2",
            "topic_3",
            "topic_4",
            "topic_5",
            "topic_6",
            "topic_7",
            "topic_8",
            "topic_9",
            "editor",
            "editor_location",
            "skoufas_classification",
            "language",
            "edition",
            "edition_year",
            "pages",
            "copies",
            "volumes",
            "notes",
            "material",
            "isbn",
            "issn",
            "ean",
            "offprint",
            "has_cd",
            "has_dvd",
            "donor_1",
            "donor_2",
            "donor_3",
        ]

    async def convert_book_entry_to_csv_row(self, book_entry: BookEntry, entry_number_object: EntryNumber) -> list[Any]:
        """Conversion function that takes a single book and returns a list of csv fields."""
        if entry_number_object:
            entry_number = entry_number_object.entry_number
        else:
            entry_number = ""
        title = book_entry.title
        subtitle = book_entry.subtitle
        author_1 = ""
        author_2 = ""
        author_3 = ""
        author_4 = ""
        idx = 0
        async for author in book_entry.authors.all():
            idx += 1
            if idx == 1:
                author_1 = str(author)
            elif idx == 2:
                author_2 = str(author)
            elif idx == 3:
                author_3 = str(author)
            elif idx == 4:
                author_4 = str(author)
            else:
                raise Exception(f"{title} has more than 4 authors")

        translator_1 = ""
        translator_2 = ""
        translator_3 = ""
        idx = 0
        async for translator in book_entry.translators.all():
            idx += 1
            if idx == 1:
                translator_1 = str(translator)
            elif idx == 2:
                translator_2 = str(translator)
            elif idx == 3:
                translator_3 = str(translator)
            else:
                raise Exception(f"{title} has more than 3 translators")
        curator_1 = ""
        curator_2 = ""
        curator_3 = ""
        idx = 0
        async for curator in book_entry.curators.all():
            idx += 1
            if idx == 1:
                curator_1 = str(curator)
            elif idx == 2:
                curator_2 = str(curator)
            elif idx == 3:
                curator_3 = str(curator)
            else:
                raise Exception(f"{title} has more than 3 curators")
        topic_1 = ""
        topic_2 = ""
        topic_3 = ""
        topic_4 = ""
        topic_5 = ""
        topic_6 = ""
        topic_7 = ""
        topic_8 = ""
        topic_9 = ""
        idx = 0
        async for topic in book_entry.topics.all():
            idx += 1
            if idx == 1:
                topic_1 = str(topic)
            elif idx == 2:
                topic_2 = str(topic)
            elif idx == 3:
                topic_3 = str(topic)
            elif idx == 4:
                topic_4 = str(topic)
            elif idx == 5:
                topic_5 = str(topic)
            elif idx == 6:
                topic_6 = str(topic)
            elif idx == 7:
                topic_7 = str(topic)
            elif idx == 8:
                topic_8 = str(topic)
            elif idx == 9:
                topic_9 = str(topic)
            else:
                raise Exception(f"{title} has more than 9 topics")
        editor = book_entry.editor.name if book_entry.editor else ""
        editor_location = book_entry.editor.place if book_entry.editor else ""
        skoufas_classification = book_entry.skoufas_classification
        language = book_entry.language
        edition = book_entry.edition
        edition_year = book_entry.edition_year
        pages = book_entry.pages
        copies = book_entry.copies
        volumes = book_entry.volumes
        notes = book_entry.notes
        material = book_entry.material
        isbn = book_entry.isbn
        issn = book_entry.issn
        ean = book_entry.ean
        offprint = "Y" if book_entry.offprint else "N"
        has_cd = "Y" if book_entry.has_cd else "N"
        has_dvd = "Y" if book_entry.has_dvd else "N"
        donor_1 = ""
        donor_2 = ""
        donor_3 = ""
        donors = set()
        if entry_number_object:
            async for donor in entry_number_object.entry_number_donors.all():
                donors.add(str(donor))
        async for donor in book_entry.entry_donors.all():
            donors.add(str(donor))
        for idx, donor_str in enumerate(list(donors)):
            if idx == 0:
                donor_1 = donor_str
            elif idx == 1:
                donor_2 = donor_str
            elif idx == 2:
                donor_3 = donor_str
            else:
                raise Exception(f"{title} has more than 3 donors")

        return [
            entry_number,
            title,
            subtitle,
            author_1,
            author_2,
            author_3,
            author_4,
            translator_1,
            translator_2,
            translator_3,
            curator_1,
            curator_2,
            curator_3,
            topic_1,
            topic_2,
            topic_3,
            topic_4,
            topic_5,
            topic_6,
            topic_7,
            topic_8,
            topic_9,
            editor,
            editor_location,
            skoufas_classification,
            language,
            edition,
            edition_year,
            pages,
            copies,
            volumes,
            notes,
            material,
            isbn,
            issn,
            ean,
            offprint,
            has_cd,
            has_dvd,
            donor_1,
            donor_2,
            donor_3,
        ]

    async def result(self, request):
        """Asynchronously return the CSV."""
        pseudo_buffer = self.Echo()
        writer = csv.writer(pseudo_buffer)
        yield writer.writerow(self.head_csv_row())

        async for book_entry in BookEntry.objects.order_by("edition_year", "title").select_related("editor").all():
            number_of_entry_numbers = await book_entry.entrynumber_set.acount()
            if number_of_entry_numbers > 0:
                async for entry_number in book_entry.entrynumber_set.all():
                    yield writer.writerow(await self.convert_book_entry_to_csv_row(book_entry, entry_number))
            else:
                yield writer.writerow(await self.convert_book_entry_to_csv_row(book_entry, None))

    async def get(self, request):
        """Return an async response with the result."""
        return StreamingHttpResponse(
            streaming_content=self.result(request),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="all-skoufas-books.csv"'},
        )
