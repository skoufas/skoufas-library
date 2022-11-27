import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from skoufas_dbf_reader.field_extractors import *
from skoufas_dbf_reader.utilities import all_entries
from skoufas_dbf_reader.generate_reports import check_ean, check_isbn, check_issn

from books.models import (
    Author,
    Translator,
    Curator,
    Donor,
    BookEntry,
    DbfEntry,
    DbfEntryRow,
    Editor,
    EntryNumber,
    Topic,
)


class Command(BaseCommand):
    help = "Import books"

    def add_authors(self, entry: dict[int, str]) -> list[Author]:
        result: list[Author] = []
        authors = authors_from_a01(entry[1])
        if not authors:
            self.stdout.write(f"{entry[0]}: No authors for {entry[0]}")
            return result
        for author in authors:
            split_author = author.split(",")
            if len(split_author) == 2:
                author_entry, author_created = Author.objects.get_or_create(
                    first_name=split_author[1],
                    surname=split_author[0],
                    middle_name="",
                    organisation_name=None,
                )
            elif len(split_author) == 1:
                author_entry, author_created = Author.objects.get_or_create(
                    first_name=None,
                    surname=None,
                    middle_name=None,
                    organisation_name=split_author[0],
                )
            else:
                author_entry = None
                author_created = False

            if not author_entry:
                self.stderr.write(f"{entry[0]}: Cannot create translator {author}")
            else:
                result.append(author_entry)
                if author_created:
                    author_entry.save()
                    self.stdout.write(f"{entry[0]}: Added author {author} with id { author_entry.id }")
                else:
                    self.stdout.write(f"{entry[0]}: Reusing author {author}")
        return result

    def add_translators(self, entry: dict[int, str]) -> list[Translator]:
        result: list[Translator] = []
        translator_value = translator_from_a06(entry[6])
        if not translator_value:
            self.stdout.write(f"{entry[0]}: No translators for {entry[0]}")
            return result
        translators = translator_value.split("!!")
        for translator in translators:
            split_translator = translator.split(",")
            if len(split_translator) == 2:
                translator_entry, translator_created = Translator.objects.get_or_create(
                    first_name=split_translator[1],
                    surname=split_translator[0],
                    middle_name="",
                    organisation_name=None,
                )
            elif len(split_translator) == 1:
                translator_entry, translator_created = Translator.objects.get_or_create(
                    first_name=None,
                    surname=None,
                    middle_name=None,
                    organisation_name=split_translator[0],
                )
            else:
                translator_entry = None
                translator_created = False

            if not translator_entry:
                self.stderr.write(f"{entry[0]}: Cannot create translator {translator}")
            else:
                result.append(translator_entry)
                if translator_created:
                    translator_entry.save()
                    self.stdout.write(f"{entry[0]}: Added translator {translator} with id { translator_entry.id }")
                else:
                    self.stdout.write(f"{entry[0]}: Reusing translator {translator}")
        return result

    def add_curators(self, entry: dict[int, str]) -> list[Curator]:
        result: list[Curator] = []
        curator_value = curator_from_a16(entry[16])
        if not curator_value:
            self.stdout.write(f"{entry[0]}: No curators for {entry[0]}")
            return result
        curators = curator_value.split("!!")
        for curator in curators:
            split_curator = curator.split(",")
            if len(split_curator) == 2:
                curator_entry, curator_created = Curator.objects.get_or_create(
                    first_name=split_curator[1],
                    surname=split_curator[0],
                    middle_name="",
                    organisation_name=None,
                )
            elif len(split_curator) == 1:
                curator_entry, curator_created = Curator.objects.get_or_create(
                    first_name=None,
                    surname=None,
                    middle_name=None,
                    organisation_name=split_curator[0],
                )
            else:
                curator_entry = None
                curator_created = False
            if not curator_entry:
                self.stderr.write(f"{entry[0]}: Cannot create curator {curator}")
            else:
                result.append(curator_entry)
                if curator_created:
                    curator_entry.save()
                    self.stdout.write(f"{entry[0]}: Added curator {curator} with id { curator_entry.id }")
                else:
                    self.stdout.write(f"{entry[0]}: Reusing curator {curator}")
        return result

    def add_donors(self, entry: dict[int, str]) -> list[Donor]:
        result: list[Donor] = []
        donors = donation_from_a17_a30(entry[17], entry[30])
        if not donors:
            self.stdout.write(f"{entry[0]}: No donors for {entry[0]}")
            return result
        for donor in donors.split("!!"):
            split_donor = donor.split(",")
            if len(split_donor) == 2:
                donor_entry, donor_created = Donor.objects.get_or_create(
                    first_name=split_donor[1],
                    surname=split_donor[0],
                    middle_name="",
                    organisation_name=None,
                )
            elif len(split_donor) == 1:
                donor_entry, donor_created = Donor.objects.get_or_create(
                    first_name=None,
                    surname=None,
                    middle_name=None,
                    organisation_name=split_donor[0],
                )
            else:
                donor_entry = None
                donor_created = False
            if not donor_entry:
                self.stderr.write(f"{entry[0]}: Cannot create donor {donor}")
            else:
                result.append(donor_entry)
                if donor_created:
                    donor_entry.save()
                    self.stdout.write(f"{entry[0]}: Added donor {donor} with id { donor_entry.id }")
                else:
                    self.stdout.write(f"{entry[0]}: Reusing donor {donor}")
        return result

    def add_editor(self, entry: dict[int, str]) -> Optional[Editor]:
        editor_place = editor_from_a08_a09(entry[8], entry[9])
        if not editor_place:
            return None
        (editor, place) = editor_place
        editor_entry, editor_created = Editor.objects.get_or_create(
            name=editor,
            place=place,
        )
        if not editor_entry:
            self.stderr.write(f"{entry[0]}: Cannot create editor {editor} {place}")
        else:
            if editor_created:
                editor_entry.save()
                self.stdout.write(f"{entry[0]}: Added editor {editor} {place} with id { editor_entry.id }")
            else:
                self.stdout.write(f"{entry[0]}: Reusing editor {editor} {place}")
        return editor_entry

    def add_topics(self, entry: dict[int, str]) -> list[Topic]:
        result: list[Topic] = []
        topic_list = topics_from_a12_to_a15_a20_a22_to_a24(
            [
                entry[12],
                entry[13],
                entry[14],
                entry[15],
                entry[20],
                entry[22],
                entry[23],
                entry[24],
            ]
        )
        for topic in topic_list:
            topic_entry, topic_created = Topic.objects.get_or_create(
                topic_name=topic,
            )
            if not topic_entry:
                self.stderr.write(f"{entry[0]}: Cannot create topic {topic}")
            else:
                result.append(topic_entry)
                if topic_created:
                    topic_entry.save()
                    self.stdout.write(f"{entry[0]}: Added topic {topic} with id { topic_entry.id }")
                else:
                    self.stdout.write(f"{entry[0]}: Reusing topic {topic}")
        return result

    def add_original_entry(
        self,
        entry: dict[int, str],
        book_entry,
        import_time,
    ) -> DbfEntry:
        # Original DBF Entry
        dbf_entry, entry_created = DbfEntry.objects.get_or_create(
            dbf_sequence=entry[0],
            book_entry=book_entry,
            defaults={
                "import_time": import_time,
            },
        )

        # Original DBF Rows
        for (k, v) in entry.items():
            if v:
                DbfEntryRow.objects.get_or_create(
                    dbfentry=dbf_entry,
                    code=k,
                    defaults={"value": v},
                )
        if not dbf_entry:
            self.stderr.write(f"{entry[0]}: Cannot create original dbf entry")
        else:
            if entry_created:
                dbf_entry.save()
                self.stdout.write(f"{entry[0]}: Added original dbf entry with id { dbf_entry.id }")
            else:
                self.stderr.write(f"{entry[0]}: Reusing original dbf entry????")
        return dbf_entry

    def add_book_entry(
        self,
        entry: dict[int, str],
        authors,
        translators,
        curators,
        donors,
        editor,
        topics,
    ) -> BookEntry:
        title = title_from_a02(entry[2])
        subtitle = subtitle_from_a03(entry[3])
        dewey = dewey_from_a04(entry[4])
        language = language_from_a01(entry[1])
        edition = edition_from_a07(entry[7])
        edition_year = edition_year_from_a09_a10(entry[9], entry[10])
        pages = pages_from_a11(entry[11])
        copies = copies_from_a17_a18_a30(entry[17], entry[18], entry[30])
        volume = volume_from_a17_a18_a20_a30(entry[17], entry[18], entry[20], entry[30])
        material = material_from_a18_a30(entry[18], entry[30])
        notes = notes_from_a17_a18_a21_a30(entry[17], entry[18], entry[21], entry[30])
        isbn_issn_ean = isbn_from_a17_a18_a19_a22_a30(entry[17], entry[18], entry[19], entry[22], entry[30])
        isbn = None
        issn = None
        ean = None
        if isbn_issn_ean:
            if not check_isbn(isbn_issn_ean):
                isbn = isbn_issn_ean
            if not check_issn(isbn_issn_ean):
                issn = isbn_issn_ean
            if not check_ean(isbn_issn_ean):
                ean = isbn_issn_ean
        has_cd = has_cd_from_a02_a03_a12_a13_a14_a17_a18_a22_a30(
            [
                entry[2],
                entry[3],
                entry[12],
                entry[13],
                entry[14],
                entry[17],
                entry[18],
                entry[22],
                entry[30],
            ]
        )
        has_dvd = has_dvd_from_a30(
            [
                entry[30],
            ]
        )
        is_offprint = offprint_from_a17_a21_a30(entry[17], entry[21], entry[30])

        book_entry, entry_created = BookEntry.objects.get_or_create(
            editor=editor,
            title=title,
            subtitle=subtitle,
            dewey=dewey,
            language=language,
            edition=edition,
            edition_year=edition_year,
            pages=pages,
            copies=copies,
            volumes=volume,
            notes=notes,
            material=material,
            isbn=isbn,
            issn=issn,
            ean=ean,
            offprint=is_offprint,
            has_cd=has_cd,
            has_dvd=has_dvd,
        )

        if not book_entry:
            self.stderr.write(f"{entry[0]}: Cannot create book entry")
        else:
            if entry_created:
                book_entry.authors.set(authors),
                book_entry.translators.set(translators),
                book_entry.curators.set(curators),
                book_entry.topics.set(topics)
                book_entry.entry_donors.set(donors)
                book_entry.save()
                self.stdout.write(f"{entry[0]}: Added book entry")
            else:
                self.stderr.write(f"{entry[0]}: Reusing book entry????")
        return book_entry

    def add_entry_numbers(self, entry, book_entry, donors):
        entry_numbers = entry_numbers_from_a05_a06_a07_a08_a18_a19(
            entry[5], entry[6], entry[7], entry[8], entry[18], entry[19]
        )
        copies = copies_from_a17_a18_a30(entry[17], entry[18], entry[30])

        if not entry_numbers:
            return
        result = []
        for entry_number in entry_numbers:
            entry_number_object, entry_created = EntryNumber.objects.get_or_create(
                entry_number=entry_number,
                defaults={
                    "book_entry": book_entry,
                },
            )
            if not entry_number_object:
                self.stderr.write(f"{entry[0]}: Cannot create entry number for {entry_number}")
            else:
                if not entry_created:
                    previous_book_entry = entry_number_object.book_entry
                    self.stderr.write(
                        f"{entry[0]}: entry number {entry_number} is already used by {previous_book_entry}. Replacing."
                    )
                entry_number_object.copies = copies
                entry_number_object.book_entry = book_entry
                entry_number_object.save()
                entry_number_object.entry_number_donors.set(donors)
                self.stdout.write(f"{entry[0]}: Added entry number {entry_number}")

    def handle(self, *args, **options):
        usr = User.objects.get(username="admin")
        usr.set_password("admin")
        usr.save()
        now = datetime.datetime.utcnow()

        for entry in all_entries():
            self.stdout.write(f"\n---- {entry[0]} ----")
            authors = self.add_authors(entry)
            translators = self.add_translators(entry)
            curators = self.add_curators(entry)
            donors = self.add_donors(entry)
            editor = self.add_editor(entry)
            topics = self.add_topics(entry)
            book_entry = self.add_book_entry(
                entry=entry,
                authors=authors,
                translators=translators,
                curators=curators,
                donors=donors,
                editor=editor,
                topics=topics,
            )
            entry_numbers = self.add_entry_numbers(entry=entry, book_entry=book_entry, donors=donors)

            self.add_original_entry(
                entry,
                book_entry,
                now,
            )
