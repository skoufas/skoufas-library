"""Views for exporting the catalogue as CSV or MARC 21 records."""

import csv
import io
from typing import Any

import pymarc
from asgiref.sync import sync_to_async
from pymarc import Indicators
from pymarc import Subfield

from django.http import Http404, StreamingHttpResponse
from django.shortcuts import render
from django.views import View

from books.models import BookEntry, BookEntryImage, EntryNumber, Location


class CSVExportView(View):
    """A view that streams a large CSV file with all book entries."""

    class Echo:
        """An object that implements just the write method of the file-like interface."""

        def write(self, value):
            """Write the value by returning it, instead of storing in a buffer."""
            return value

    def head_csv_row(self, include_location: bool = False) -> list[str]:
        """Return a list of CSV column names."""
        # Overlaps with curation.queries.BOOK_SCALAR_FIELDS (same field names),
        # but this is the CSV's own presentation order/columns (including
        # author_1..6 etc.), not the same list - sharing a constant would
        # wrongly couple CSV export formatting to curation's internal
        # duplicate-detection field list.
        # pylint: disable=duplicate-code
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
        # pylint: enable=duplicate-code
        if include_location:
            row.append("location")
        return row

    # Wide, sequential slot-filling for a fixed CSV column layout - splitting it up
    # would just thread the same values through several helper calls.
    # pylint: disable-next=too-many-locals,too-many-branches,too-many-statements
    async def convert_book_entry_to_csv_row(
        self, book_entry: BookEntry, entry_number_object: EntryNumber | None, include_location: bool = False
    ) -> list[Any]:
        """Conversion function that takes a single book and returns a list of csv fields."""
        entry_number: int | str
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

    async def result(self, include_location: bool = False):
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
            streaming_content=self.result(include_location=include_location),
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

    # A sequence of mostly-independent MARC field-mapping blocks (control fields,
    # contributors, title, identifiers, holdings, images...) - inherently long.
    # pylint: disable-next=too-many-locals,too-many-branches,too-many-statements
    async def _book_entry_to_marc(
        self,
        book_entry: BookEntry,
        include_holdings: bool,
        can_see_nonpublic: bool,
        request: Any,
    ) -> pymarc.Record:
        record = pymarc.Record(force_utf8=True)

        # --- Control fields ---
        record.add_field(pymarc.Field(tag="001", data=str(book_entry.pk)))
        record.add_field(pymarc.Field(tag="003", data=self.MARC_ORG_CODE))

        # 041 – Language
        marc_lang = self._marc_lang(book_entry.language)
        if marc_lang:
            record.add_field(
                pymarc.Field(tag="041", indicators=Indicators(" ", " "), subfields=[Subfield("a", marc_lang)])
            )

        # 082 – Dewey / Skoufas classification
        if book_entry.skoufas_classification:
            record.add_field(
                pymarc.Field(
                    tag="082",
                    indicators=Indicators("0", "4"),
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
                record.add_field(pymarc.Field(tag=tag, indicators=Indicators("2", " "), subfields=sf))
            else:
                name = self._personal_name_inverted(author.surname, author.first_name, author.middle_name)
                if not name and author.pseudonym:
                    name = str(author.pseudonym)
                tag = "100" if first_author else "700"
                sf = [Subfield("a", name)]
                if not first_author:
                    sf.append(Subfield("e", "author"))
                record.add_field(pymarc.Field(tag=tag, indicators=Indicators("1", " "), subfields=sf))
            first_author = False

        # 245 – Title / Subtitle
        title = book_entry.title or ""
        subtitle = book_entry.subtitle or ""
        ind1 = "0" if first_author else "1"  # first_author still True means no authors added
        title_sf = [Subfield("a", title)]
        if subtitle:
            title_sf.append(Subfield("b", subtitle))
        if title or subtitle:
            record.add_field(pymarc.Field(tag="245", indicators=Indicators(ind1, "0"), subfields=title_sf))

        # 250 – Edition
        if book_entry.edition:
            record.add_field(
                pymarc.Field(tag="250", indicators=Indicators(" ", " "), subfields=[Subfield("a", book_entry.edition)])
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
            record.add_field(pymarc.Field(tag="260", indicators=Indicators(" ", " "), subfields=pub_sf))

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
            record.add_field(pymarc.Field(tag="300", indicators=Indicators(" ", " "), subfields=phys_sf))

        # 020 / 022 / 024 – Identifiers
        if book_entry.isbn:
            record.add_field(
                pymarc.Field(
                    tag="020", indicators=Indicators(" ", " "), subfields=[Subfield("a", str(book_entry.isbn))]
                )
            )
        if book_entry.issn:
            record.add_field(
                pymarc.Field(
                    tag="022", indicators=Indicators(" ", " "), subfields=[Subfield("a", str(book_entry.issn))]
                )
            )
        if book_entry.ean:
            record.add_field(
                pymarc.Field(tag="024", indicators=Indicators("3", " "), subfields=[Subfield("a", str(book_entry.ean))])
            )

        # 500 – General notes
        if book_entry.notes:
            record.add_field(
                pymarc.Field(tag="500", indicators=Indicators(" ", " "), subfields=[Subfield("a", book_entry.notes)])
            )
        if book_entry.material:
            record.add_field(
                pymarc.Field(tag="500", indicators=Indicators(" ", " "), subfields=[Subfield("a", book_entry.material)])
            )
        if book_entry.offprint:
            record.add_field(
                pymarc.Field(tag="500", indicators=Indicators(" ", " "), subfields=[Subfield("a", "Offprint")])
            )

        # 541 – Donors (book-level)
        async for donor in book_entry.entry_donors.all():
            record.add_field(
                pymarc.Field(tag="541", indicators=Indicators(" ", " "), subfields=[Subfield("a", str(donor))])
            )

        # 650 – Topics (local subject headings)
        async for topic in book_entry.topics.all():
            record.add_field(
                pymarc.Field(tag="650", indicators=Indicators(" ", "4"), subfields=[Subfield("a", str(topic))])
            )

        # 700 / 710 – Translators
        async for translator in book_entry.translators.all():
            if translator.organisation_name:
                record.add_field(
                    pymarc.Field(
                        tag="710",
                        indicators=Indicators("2", " "),
                        subfields=[Subfield("a", str(translator.organisation_name)), Subfield("e", "translator")],
                    )
                )
            else:
                name = self._personal_name_inverted(translator.surname, translator.first_name, translator.middle_name)
                record.add_field(
                    pymarc.Field(
                        tag="700",
                        indicators=Indicators("1", " "),
                        subfields=[Subfield("a", name), Subfield("e", "translator")],
                    )
                )

        # 700 / 710 – Curators (relator: editor)
        async for curator in book_entry.curators.all():
            if curator.organisation_name:
                record.add_field(
                    pymarc.Field(
                        tag="710",
                        indicators=Indicators("2", " "),
                        subfields=[Subfield("a", str(curator.organisation_name)), Subfield("e", "editor")],
                    )
                )
            else:
                name = self._personal_name_inverted(curator.surname, curator.first_name, curator.middle_name)
                record.add_field(
                    pymarc.Field(
                        tag="700",
                        indicators=Indicators("1", " "),
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
                    while (parent := building.parent) is not None:
                        building = parent

                    sf952: list[Subfield] = [
                        Subfield("a", building.name),
                        Subfield("b", building.name),
                        Subfield("c", en.location.full_path()),
                        Subfield("p", str(en.entry_number)),
                        Subfield("y", "BK"),
                    ]
                    # Mark non-public items as restricted in Koha (952$5=1)
                    if is_nonpublic:
                        sf952.append(Subfield("5", "1"))
                else:
                    is_nonpublic = False
                    sf952 = [
                        Subfield("p", str(en.entry_number)),
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

                record.add_field(pymarc.Field(tag="952", indicators=Indicators(" ", " "), subfields=sf952))

        # 856 – Electronic location (cover/back-cover/other images)
        _image_type_label: dict[str, str] = {
            BookEntryImage.ImageType.COVER: "Cover image",
            BookEntryImage.ImageType.BACK_COVER: "Back cover image",
            BookEntryImage.ImageType.INTERNAL: "Internal image",
            BookEntryImage.ImageType.OTHER: "Image",
        }
        async for img in book_entry.images.order_by("order").all():
            ind2 = "1" if img.image_type == BookEntryImage.ImageType.COVER else "3"
            sf856: list[Subfield] = [
                Subfield("u", request.build_absolute_uri(img.image.url)),
                Subfield("3", _image_type_label.get(img.image_type, "Image")),
                Subfield("q", "image/jpeg"),
            ]
            if img.caption:
                sf856.append(Subfield("z", img.caption))
            record.add_field(pymarc.Field(tag="856", indicators=Indicators("4", ind2), subfields=sf856))

        return record

    async def _iter_records(self, request: Any):
        user = await request.auser()
        include_holdings: bool = user.is_authenticated
        can_see_nonpublic: bool = include_holdings and user.has_perm("books.view_nonpublic_location")
        async for book_entry in BookEntry.objects.order_by("edition_year", "title").select_related("editor").all():
            yield await self._book_entry_to_marc(book_entry, include_holdings, can_see_nonpublic, request)

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
        pk = self.kwargs["pk"]
        try:
            book_entry = await BookEntry.objects.select_related("editor").aget(pk=pk)
        except BookEntry.DoesNotExist:
            raise Http404 from None
        user = await request.auser()
        include_holdings: bool = user.is_authenticated
        can_see_nonpublic: bool = include_holdings and user.has_perm("books.view_nonpublic_location")
        yield await self._book_entry_to_marc(book_entry, include_holdings, can_see_nonpublic, request)

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

    # Inherits from MARCExportView only to reuse _book_entry_to_marc/_stream_*;
    # its get() has its own URL contract (pk, not fmt) and is never dispatched
    # polymorphically as a MARCExportView.
    async def get(self, request: Any, pk: int, **_kwargs: Any):  # type: ignore[override]  # pylint: disable=arguments-renamed
        try:
            book_entry = await BookEntry.objects.select_related("editor").aget(pk=pk)
        except BookEntry.DoesNotExist:
            raise Http404 from None

        user = await request.auser()
        include_holdings: bool = user.is_authenticated
        can_see_nonpublic: bool = include_holdings and user.has_perm("books.view_nonpublic_location")
        record = await self._book_entry_to_marc(book_entry, include_holdings, can_see_nonpublic, request)

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
