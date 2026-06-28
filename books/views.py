"""Views on Books."""

import csv
import io
from typing import Any

import numpy as np
import cv2
import pillow_heif
import pymarc
from PIL import Image
from pymarc import Subfield

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from books.models import Author, BookEntry, BookEntryImage, Donor, EntryNumber, Location
from books.skoufas_classification_classes import classification
from curation.models import InventorySession


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

    def head_csv_row(self, include_location: bool = False) -> list[str]:
        """Return a list of CSV column names."""
        row = [
            "entry_number",
            "title",
            "subtitle",
            "author_1",
            "author_2",
            "author_3",
            "author_4",
            "author_5",
            "author_6",
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
        if include_location:
            row.append("location")
        return row

    async def convert_book_entry_to_csv_row(
        self, book_entry: BookEntry, entry_number_object: EntryNumber, include_location: bool = False
    ) -> list[Any]:
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
        author_5 = ""
        author_6 = ""
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
            elif idx == 5:
                author_5 = str(author)
            elif idx == 6:
                author_6 = str(author)
            else:
                raise Exception(f"{title} has more than 6 authors")

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
        for idx, donor_str in enumerate(sorted(donors)):
            if idx == 0:
                donor_1 = donor_str
            elif idx == 1:
                donor_2 = donor_str
            elif idx == 2:
                donor_3 = donor_str
            else:
                raise Exception(f"{title} has more than 3 donors")

        row = [
            entry_number,
            title,
            subtitle,
            author_1,
            author_2,
            author_3,
            author_4,
            author_5,
            author_6,
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
        if include_location:
            if entry_number_object and entry_number_object.location_id:
                row.append(str(entry_number_object.location))
            else:
                row.append("")
        return row

    async def result(self, request, include_location: bool = False):
        """Asynchronously return the CSV."""
        pseudo_buffer = self.Echo()
        writer = csv.writer(pseudo_buffer)
        yield writer.writerow(self.head_csv_row(include_location=include_location))

        async for book_entry in BookEntry.objects.order_by("edition_year", "title").select_related("editor").all():
            number_of_entry_numbers = await book_entry.entrynumber_set.acount()
            if number_of_entry_numbers > 0:
                async for entry_number in book_entry.entrynumber_set.select_related(
                    "location__parent__parent__parent"
                ).all():
                    yield writer.writerow(
                        await self.convert_book_entry_to_csv_row(
                            book_entry, entry_number, include_location=include_location
                        )
                    )
            else:
                yield writer.writerow(
                    await self.convert_book_entry_to_csv_row(book_entry, None, include_location=include_location)
                )

    async def get(self, request):
        """Return an async response with the result."""
        user = await request.auser()
        include_location = user.is_authenticated
        return StreamingHttpResponse(
            streaming_content=self.result(request, include_location=include_location),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="all-skoufas-books.csv"'},
        )


class MARCExportView(View):
    """A view that streams MARC 21 records for all book entries.

    Three serialisations are supported, selected by the ``fmt`` URL kwarg:
    - ``mrc``  → ISO 2709 binary  (application/marc)
    - ``xml``  → MARCXML          (application/marcxml+xml)
    - ``mrk``  → MARCMaker text   (text/plain)

    Bibliographic fields are always public.  Koha item fields (952) are
    only included for authenticated users; non-public locations are
    additionally filtered for users without ``books.view_nonpublic_location``.
    """

    MARC_ORG_CODE = "GR-ArMPA"

    # ISO 639-1 / ISO 639-3 codes stored in DB → MARC language codes
    LANGUAGE_TO_MARC: dict[str, str] = {
        "el": "gre",
        "en": "eng",
        "de": "ger",
        "fr": "fre",
        "it": "ita",
        "es": "spa",
        "nl": "dut",
        "pt": "por",
        "ru": "rus",
        "ar": "ara",
        # Already 3-letter; use as-is
        "cpg": "cpg",
        "gmy": "gmy",
        "grc": "grc",
        "grk": "grk",
        "gss": "gss",
        "rge": "rge",
    }

    def _marc_lang(self, code: str | None) -> str | None:
        if not code:
            return None
        return self.LANGUAGE_TO_MARC.get(code, code if len(code) == 3 else None)

    def _personal_name_inverted(self, surname: str | None, first_name: str | None, middle_name: str | None) -> str:
        parts: list[str] = []
        if surname:
            parts.append(surname + ("," if first_name or middle_name else ""))
        if first_name:
            parts.append(first_name)
        if middle_name:
            parts.append(middle_name)
        return " ".join(parts)

    async def _book_entry_to_marc(
        self,
        book_entry: BookEntry,
        include_holdings: bool,
        can_see_nonpublic: bool,
    ) -> pymarc.Record:
        record = pymarc.Record(force_utf8=True)

        # --- Control fields ---
        record.add_field(pymarc.Field(tag="001", data=str(book_entry.pk)))
        record.add_field(pymarc.Field(tag="003", data=self.MARC_ORG_CODE))

        # 041 – Language
        marc_lang = self._marc_lang(book_entry.language)
        if marc_lang:
            record.add_field(pymarc.Field(tag="041", indicators=[" ", " "], subfields=[Subfield("a", marc_lang)]))

        # 082 – Dewey / Skoufas classification
        if book_entry.skoufas_classification:
            record.add_field(
                pymarc.Field(
                    tag="082",
                    indicators=["0", "4"],
                    subfields=[Subfield("a", book_entry.skoufas_classification)],
                )
            )

        # 100 / 110 / 700 / 710 – Authors
        first_author = True
        async for author in book_entry.authors.all():
            if author.organisation_name:
                tag = "110" if first_author else "710"
                sf = [Subfield("a", str(author.organisation_name))]
                if not first_author:
                    sf.append(Subfield("e", "author"))
                record.add_field(pymarc.Field(tag=tag, indicators=["2", " "], subfields=sf))
            else:
                name = self._personal_name_inverted(author.surname, author.first_name, author.middle_name)
                if not name and author.pseudonym:
                    name = str(author.pseudonym)
                tag = "100" if first_author else "700"
                sf = [Subfield("a", name)]
                if not first_author:
                    sf.append(Subfield("e", "author"))
                record.add_field(pymarc.Field(tag=tag, indicators=["1", " "], subfields=sf))
            first_author = False

        # 245 – Title / Subtitle
        title = book_entry.title or ""
        subtitle = book_entry.subtitle or ""
        ind1 = "0" if first_author else "1"  # first_author still True means no authors added
        title_sf = [Subfield("a", title)]
        if subtitle:
            title_sf.append(Subfield("b", subtitle))
        if title or subtitle:
            record.add_field(pymarc.Field(tag="245", indicators=[ind1, "0"], subfields=title_sf))

        # 250 – Edition
        if book_entry.edition:
            record.add_field(
                pymarc.Field(tag="250", indicators=[" ", " "], subfields=[Subfield("a", book_entry.edition)])
            )

        # 260 – Publication info
        pub_sf: list[Subfield] = []
        if book_entry.editor:
            if book_entry.editor.place:
                pub_sf.append(Subfield("a", book_entry.editor.place))
            if book_entry.editor.name:
                pub_sf.append(Subfield("b", book_entry.editor.name))
        if book_entry.edition_year:
            pub_sf.append(Subfield("c", str(book_entry.edition_year)))
        if pub_sf:
            record.add_field(pymarc.Field(tag="260", indicators=[" ", " "], subfields=pub_sf))

        # 300 – Physical description
        phys_sf: list[Subfield] = []
        if book_entry.pages:
            phys_sf.append(Subfield("a", f"{book_entry.pages} p."))
        if book_entry.volumes:
            phys_sf.append(Subfield("f", book_entry.volumes))
        acc: list[str] = []
        if book_entry.has_cd:
            acc.append("1 CD-ROM")
        if book_entry.has_dvd:
            acc.append("1 DVD")
        if acc:
            phys_sf.append(Subfield("e", " + ".join(acc)))
        if phys_sf:
            record.add_field(pymarc.Field(tag="300", indicators=[" ", " "], subfields=phys_sf))

        # 020 / 022 / 024 – Identifiers
        if book_entry.isbn:
            record.add_field(
                pymarc.Field(tag="020", indicators=[" ", " "], subfields=[Subfield("a", str(book_entry.isbn))])
            )
        if book_entry.issn:
            record.add_field(
                pymarc.Field(tag="022", indicators=[" ", " "], subfields=[Subfield("a", str(book_entry.issn))])
            )
        if book_entry.ean:
            record.add_field(
                pymarc.Field(tag="024", indicators=["3", " "], subfields=[Subfield("a", str(book_entry.ean))])
            )

        # 500 – General notes
        if book_entry.notes:
            record.add_field(
                pymarc.Field(tag="500", indicators=[" ", " "], subfields=[Subfield("a", book_entry.notes)])
            )
        if book_entry.material:
            record.add_field(
                pymarc.Field(tag="500", indicators=[" ", " "], subfields=[Subfield("a", book_entry.material)])
            )
        if book_entry.offprint:
            record.add_field(pymarc.Field(tag="500", indicators=[" ", " "], subfields=[Subfield("a", "Offprint")]))

        # 541 – Donors (book-level)
        async for donor in book_entry.entry_donors.all():
            record.add_field(pymarc.Field(tag="541", indicators=[" ", " "], subfields=[Subfield("a", str(donor))]))

        # 650 – Topics (local subject headings)
        async for topic in book_entry.topics.all():
            record.add_field(pymarc.Field(tag="650", indicators=[" ", "4"], subfields=[Subfield("a", str(topic))]))

        # 700 / 710 – Translators
        async for translator in book_entry.translators.all():
            if translator.organisation_name:
                record.add_field(
                    pymarc.Field(
                        tag="710",
                        indicators=["2", " "],
                        subfields=[Subfield("a", str(translator.organisation_name)), Subfield("e", "translator")],
                    )
                )
            else:
                name = self._personal_name_inverted(translator.surname, translator.first_name, translator.middle_name)
                record.add_field(
                    pymarc.Field(
                        tag="700",
                        indicators=["1", " "],
                        subfields=[Subfield("a", name), Subfield("e", "translator")],
                    )
                )

        # 700 / 710 – Curators (relator: editor)
        async for curator in book_entry.curators.all():
            if curator.organisation_name:
                record.add_field(
                    pymarc.Field(
                        tag="710",
                        indicators=["2", " "],
                        subfields=[Subfield("a", str(curator.organisation_name)), Subfield("e", "editor")],
                    )
                )
            else:
                name = self._personal_name_inverted(curator.surname, curator.first_name, curator.middle_name)
                record.add_field(
                    pymarc.Field(
                        tag="700",
                        indicators=["1", " "],
                        subfields=[Subfield("a", name), Subfield("e", "editor")],
                    )
                )

        # 952 – Koha holdings (authenticated users only)
        if include_holdings:
            async for en in book_entry.entrynumber_set.select_related("location__parent__parent__parent").all():
                if en.location:
                    # Check whether location or any ancestor is non_public
                    is_nonpublic = False
                    node: Location | None = en.location
                    while node is not None:
                        if node.non_public:
                            is_nonpublic = True
                            break
                        node = node.parent if node.parent_id else None

                    # Skip entirely for unpermitted users
                    if not can_see_nonpublic and is_nonpublic:
                        continue

                    # Walk to building (root ancestor)
                    building: Location = en.location
                    while building.parent_id is not None:
                        building = building.parent

                    sf952: list[Subfield] = [
                        Subfield("a", building.name),
                        Subfield("b", building.name),
                        Subfield("c", en.location.full_path()),
                        Subfield("p", en.entry_number),
                        Subfield("y", "BK"),
                    ]
                    # Mark non-public items as restricted in Koha (952$5=1)
                    if is_nonpublic:
                        sf952.append(Subfield("5", "1"))
                else:
                    is_nonpublic = False
                    sf952 = [
                        Subfield("p", en.entry_number),
                        Subfield("y", "BK"),
                    ]

                if book_entry.skoufas_classification:
                    sf952.append(Subfield("o", book_entry.skoufas_classification))

                if en.copies and en.copies > 1:
                    sf952.append(Subfield("z", f"{en.copies} copies"))

                en_donors: list[str] = []
                async for donor in en.entry_number_donors.all():
                    en_donors.append(str(donor))
                if en_donors:
                    sf952.append(Subfield("z", "Donated by: " + ", ".join(sorted(en_donors))))

                record.add_field(pymarc.Field(tag="952", indicators=[" ", " "], subfields=sf952))

        return record

    async def _iter_records(self, request: Any):
        user = await request.auser()
        include_holdings: bool = user.is_authenticated
        can_see_nonpublic: bool = include_holdings and user.has_perm("books.view_nonpublic_location")
        async for book_entry in BookEntry.objects.order_by("edition_year", "title").select_related("editor").all():
            yield await self._book_entry_to_marc(book_entry, include_holdings, can_see_nonpublic)

    async def _stream_iso2709(self, request: Any):
        async for record in self._iter_records(request):
            yield record.as_marc()

    async def _stream_marcxml(self, request: Any):
        yield b'<?xml version="1.0" encoding="UTF-8"?>\n<collection xmlns="http://www.loc.gov/MARC21/slim">\n'
        async for record in self._iter_records(request):
            yield pymarc.record_to_xml(record)
            yield b"\n"
        yield b"</collection>\n"

    async def _stream_marcmaker(self, request: Any):
        async for record in self._iter_records(request):
            buf = io.StringIO()
            writer = pymarc.TextWriter(buf)
            writer.write(record)
            yield buf.getvalue().encode("utf-8")

    async def get(self, request: Any, fmt: str, **_kwargs: Any):
        """Return an async streaming response in the requested format."""
        if fmt == "mrc":
            return StreamingHttpResponse(
                streaming_content=self._stream_iso2709(request),
                content_type="application/marc",
                headers={"Content-Disposition": 'attachment; filename="all-skoufas-books.mrc"'},
            )
        if fmt == "xml":
            return StreamingHttpResponse(
                streaming_content=self._stream_marcxml(request),
                content_type="application/marcxml+xml",
                headers={"Content-Disposition": 'attachment; filename="all-skoufas-books.xml"'},
            )
        # fmt == "mrk"
        return StreamingHttpResponse(
            streaming_content=self._stream_marcmaker(request),
            content_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="all-skoufas-books.mrk"'},
        )


class MARCSingleBookExportView(MARCExportView):
    """Download a MARC21 record for a single BookEntry (all three serialisations)."""

    async def _iter_records(self, request: Any):
        from django.http import Http404

        pk = self.kwargs["pk"]
        try:
            book_entry = await BookEntry.objects.select_related("editor").aget(pk=pk)
        except BookEntry.DoesNotExist:
            raise Http404
        user = await request.auser()
        include_holdings: bool = user.is_authenticated
        can_see_nonpublic: bool = include_holdings and user.has_perm("books.view_nonpublic_location")
        yield await self._book_entry_to_marc(book_entry, include_holdings, can_see_nonpublic)

    async def get(self, request: Any, fmt: str, **_kwargs: Any):
        """Return a single-record response using the pk as the download filename."""
        pk = self.kwargs["pk"]
        if fmt == "mrc":
            return StreamingHttpResponse(
                streaming_content=self._stream_iso2709(request),
                content_type="application/marc",
                headers={"Content-Disposition": f'attachment; filename="{pk}.mrc"'},
            )
        if fmt == "xml":
            return StreamingHttpResponse(
                streaming_content=self._stream_marcxml(request),
                content_type="application/marcxml+xml",
                headers={"Content-Disposition": f'attachment; filename="{pk}.xml"'},
            )
        # fmt == "mrk"
        return StreamingHttpResponse(
            streaming_content=self._stream_marcmaker(request),
            content_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{pk}.mrk"'},
        )


class MARCSingleBookDetailView(MARCExportView):
    """Render a single BookEntry's MARC21 record as a Bootstrap table."""

    template_name = "books/bookentry_marc_detail.html"

    async def get(self, request: Any, pk: int, **_kwargs: Any):
        from asgiref.sync import sync_to_async
        from django.http import Http404
        from django.shortcuts import render

        try:
            book_entry = await BookEntry.objects.select_related("editor").aget(pk=pk)
        except BookEntry.DoesNotExist:
            raise Http404

        user = await request.auser()
        include_holdings: bool = user.is_authenticated
        can_see_nonpublic: bool = include_holdings and user.has_perm("books.view_nonpublic_location")
        record = await self._book_entry_to_marc(book_entry, include_holdings, can_see_nonpublic)

        fields = []
        for field in record:
            if field.is_control_field():
                fields.append({"tag": field.tag, "indicator1": "", "indicator2": "", "subfields": [("", field.data)]})
            else:
                subfields = [(sf.code, sf.value) for sf in field.subfields]
                fields.append(
                    {
                        "tag": field.tag,
                        "indicator1": field.indicator1.strip(),
                        "indicator2": field.indicator2.strip(),
                        "subfields": subfields,
                    }
                )

        return await sync_to_async(render)(
            request,
            self.template_name,
            {"object": book_entry, "marc_fields": fields},
        )


class LocationListView(ListView):
    """List top-level locations (buildings)."""

    model = Location
    template_name = "books/location_list.html"

    def get_queryset(self):
        """Return buildings only, filtering out non-public ones for unpermitted users."""
        qs = Location.objects.filter(parent__isnull=True)
        if not self.request.user.has_perm("books.view_nonpublic_location"):
            qs = qs.filter(non_public=False)
        return qs


class LocationDetailView(DetailView):
    """Detail view for a single location node."""

    model = Location
    template_name = "books/location_detail.html"

    def get_object(self, queryset=None):
        """Return the location, raising PermissionDenied if non-public and not permitted."""
        obj = super().get_object(queryset)
        if not obj.is_accessible(self.request.user):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        """Add children and descendant entry numbers to context."""
        context = super().get_context_data(**kwargs)
        location = context["object"]
        user = self.request.user
        can_see_nonpublic = user.has_perm("books.view_nonpublic_location")

        # Ancestor chain for breadcrumb (root first)
        ancestors = []
        node = location.parent
        while node is not None:
            ancestors.insert(0, node)
            node = node.parent if node.parent_id else None
        context["ancestors"] = ancestors

        # Direct children — filter non-public if needed
        children_qs = location.children.all()
        if not can_see_nonpublic:
            children_qs = children_qs.filter(non_public=False)
        context["children"] = children_qs

        # Entry numbers at this node and all descendants
        descendant_ids = location.get_descendant_ids()
        all_location_ids = [location.pk] + descendant_ids
        context["entry_numbers"] = (
            EntryNumber.objects.filter(location_id__in=all_location_ids)
            .select_related("book_entry", "location")
            .order_by("entry_number")
        )

        # Inventory session button (only for leaf locations)
        if location.type in {Location.TYPE_SHELF, Location.TYPE_BOX}:
            context["open_inventory_session"] = InventorySession.objects.filter(
                location=location, closed_at=None
            ).first()
            context["is_leaf_location"] = True
        return context


class BookEntryImageAddView(PermissionRequiredMixin, View):
    """Upload an image for a book entry."""

    permission_required = "curation.can_inventory"
    template_name = "books/bookentry_image_add.html"

    def _safe_next(self, request, fallback: str) -> str:
        """Return the next URL if it is safe, otherwise return the fallback."""
        next_url = request.POST.get("next") or request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return next_url
        return fallback

    def get(self, request, pk: int):
        """Show upload form."""
        book_entry = get_object_or_404(BookEntry, pk=pk)
        next_url = self._safe_next(request, book_entry.get_absolute_url())
        return render(
            request,
            self.template_name,
            {
                "book_entry": book_entry,
                "next_url": next_url,
                "image_type_choices": BookEntryImage.ImageType.choices,
            },
        )

    def post(self, request, pk: int):
        """Handle image upload."""
        book_entry = get_object_or_404(BookEntry, pk=pk)
        next_url = self._safe_next(request, book_entry.get_absolute_url())
        image_file = request.FILES.get("image")
        if image_file:
            pillow_heif.register_heif_opener()
            try:
                order = int(request.POST.get("order", 0))
            except ValueError, TypeError:
                order = 0
            image_type = request.POST.get("image_type", BookEntryImage.ImageType.COVER)
            if image_type not in BookEntryImage.ImageType.values:
                image_type = BookEntryImage.ImageType.COVER
            BookEntryImage.objects.create(
                book_entry=book_entry,
                image=image_file,
                image_type=image_type,
                caption=request.POST.get("caption", ""),
                order=order,
            )
        return redirect(next_url)


def _detect_book_cover(img: "np.ndarray") -> dict:
    """Return crop box {x, y, width, height} for the most prominent rectangle in img."""
    h, w = img.shape[:2]

    # --- Downsample to ≤800 px on the long edge ---
    MAX_DIM = 800
    scale = min(MAX_DIM / max(h, w), 1.0)
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]

    # ── Strategy 1: background-colour subtraction ────────────────────────────
    # Sample the four corners to estimate the background (table / surface) colour.
    # The book should be the largest region that differs from that colour.
    corner_pixels = np.array(
        [
            small[0, 0],
            small[0, -1],
            small[-1, 0],
            small[-1, -1],
            small[0, sw // 2],
            small[-1, sw // 2],
            small[sh // 2, 0],
            small[sh // 2, -1],
        ],
        dtype=np.float32,
    )
    bg_color = np.median(corner_pixels, axis=0).astype(np.uint8)
    diff = cv2.absdiff(small, bg_color.reshape(1, 1, 3))
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    # Threshold: pixels more than 30 units away from background are foreground
    _, fg_mask = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)
    kernel5 = np.ones((5, 5), np.uint8)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel5, iterations=4)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel5, iterations=2)
    contours1, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours1:
        largest = max(contours1, key=cv2.contourArea)
        area1 = cv2.contourArea(largest)
        if area1 > sh * sw * 0.04:
            bx, by, bw, bh = cv2.boundingRect(largest)
            # Reject if it's the whole frame (detection failed)
            if bw < sw * 0.98 or bh < sh * 0.98:
                pad, inv = 8, 1.0 / scale
                x = max(0, int((bx - pad) * inv))
                y = max(0, int((by - pad) * inv))
                x2 = min(w, int((bx + bw + pad) * inv))
                y2 = min(h, int((by + bh + pad) * inv))
                return {"x": x, "y": y, "width": x2 - x, "height": y2 - y}

    # ── Strategy 2: edge-based contour detection ─────────────────────────────
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    edges = cv2.Canny(blurred, 30, 120)
    kernel3 = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel3, iterations=4)
    edges = cv2.dilate(edges, kernel3, iterations=1)
    contours2, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours2 = sorted(contours2, key=cv2.contourArea, reverse=True)
    min_area = sh * sw * 0.04
    for contour in contours2[:20]:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            break
        peri = cv2.arcLength(contour, True)
        for eps in (0.01, 0.02, 0.04, 0.06, 0.10):
            approx = cv2.approxPolyDP(contour, eps * peri, True)
            if not (4 <= len(approx) <= 6):
                continue
            bx, by, bw, bh = cv2.boundingRect(approx)
            box_area = float(bw * bh)
            if box_area < min_area:
                continue
            if area / box_area > 0.45:
                pad, inv = 5, 1.0 / scale
                x = max(0, int((bx - pad) * inv))
                y = max(0, int((by - pad) * inv))
                x2 = min(w, int((bx + bw + pad) * inv))
                y2 = min(h, int((by + bh + pad) * inv))
                return {"x": x, "y": y, "width": x2 - x, "height": y2 - y}
            break

    # ── Fallback: centred portrait (2:3) crop ────────────────────────────────
    tw = int(h * 2 / 3)
    if tw <= w:
        return {"x": (w - tw) // 2, "y": 0, "width": tw, "height": h}
    th = int(w * 3 / 2)
    if th <= h:
        return {"x": 0, "y": (h - th) // 2, "width": w, "height": th}
    return {"x": 0, "y": 0, "width": w, "height": h}


class BookEntryCoverDetectView(PermissionRequiredMixin, View):
    """Detect book cover rectangle in an uploaded image and return crop coordinates."""

    permission_required = "curation.can_inventory"

    def post(self, request):
        """Accept an image, run contour detection, return JSON crop box."""
        image_file = request.FILES.get("image")
        if not image_file:
            return JsonResponse({"error": "no image"}, status=400)
        data = image_file.read()
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return JsonResponse({"error": "invalid image"}, status=400)
        return JsonResponse(_detect_book_cover(img))


def _to_jpeg_bytes(image_file) -> bytes:
    """Convert any image (including HEIC) to JPEG bytes using Pillow."""
    pillow_heif.register_heif_opener()

    image_file.seek(0)
    img = Image.open(image_file)
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


class BookEntryImageConvertView(PermissionRequiredMixin, View):
    """Convert an uploaded image to JPEG and return it — used client-side for HEIC preview."""

    permission_required = "curation.can_inventory"

    def post(self, request):
        """Accept any image file, return it as a JPEG."""

        image_file = request.FILES.get("image")
        if not image_file:
            return JsonResponse({"error": "no image"}, status=400)
        try:
            jpeg_bytes = _to_jpeg_bytes(image_file)
        except Exception:
            return JsonResponse({"error": "conversion failed"}, status=400)
        return HttpResponse(jpeg_bytes, content_type="image/jpeg")
