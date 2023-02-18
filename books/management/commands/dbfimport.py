"""Import data from converted books.dbf file."""
import datetime
import os
from typing import Any
from typing import Optional

import yaml
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from yaml import CSafeLoader

from books.models import Author
from books.models import BookEntry
from books.models import Curator
from books.models import DbfEntry
from books.models import DbfEntryRow
from books.models import Donor
from books.models import Editor
from books.models import EntryNumber
from books.models import Topic
from books.models import Translator


def read_all_entries(entries_file: str) -> Any:
    """Return all converted entries in a file."""
    start = datetime.datetime.now()
    print(f"Reading entries from {entries_file}", flush=True)
    with open(entries_file, "r", encoding="utf-8") as stream:
        parsed_yaml = yaml.load(stream, Loader=CSafeLoader)  # nosec
        result = parsed_yaml["converted_entries"]
        print(f"Read {len(result)} entries in {(datetime.datetime.now()-start).seconds}s", flush=True)
    return result


def entry_is_empty(entry: dict[str, Any]):
    """Check for empty entries."""
    if not entry["authors"]:
        if "title" not in entry:
            return True
        return len(entry["title"]) == 0
    return False


class Command(BaseCommand):
    """Import books."""

    help = "Import books"

    def add_authors(self, entry: dict[str, Any]) -> list[Author]:
        """Return author objects from an entry."""
        result: list[Author] = []
        authors = entry.get("authors", [])
        if not authors:
            self.stdout.write(f"{entry['dbase_number']}: No authors for {entry['dbase_number']}")
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
                self.stderr.write(f"{entry['dbase_number']}: Cannot create translator {author}")
            else:
                result.append(author_entry)
                if author_created:
                    author_entry.save()
                    self.stdout.write(f"{entry['dbase_number']}: Added author {author} with id { author_entry.id }")
                else:
                    self.stdout.write(f"{entry['dbase_number']}: Reusing author {author}")
        return result

    def add_translators(self, entry: dict[str, Any]) -> list[Translator]:
        """Return translator objects from an entry."""
        result: list[Translator] = []
        translators = entry.get("translators", [])
        if not translators:
            self.stdout.write(f"{entry['dbase_number']}: No translators for {entry['dbase_number']}")
            return result
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
                self.stderr.write(f"{entry['dbase_number']}: Cannot create translator {translator}")
            else:
                result.append(translator_entry)
                if translator_created:
                    translator_entry.save()
                    self.stdout.write(
                        f"{entry['dbase_number']}: Added translator {translator} with id { translator_entry.id }"
                    )
                else:
                    self.stdout.write(f"{entry['dbase_number']}: Reusing translator {translator}")
        return result

    def add_curator(self, entry: dict[str, Any]) -> list[Curator]:
        """Return curator objects from an entry."""
        result: list[Curator] = []
        curator = entry.get("curator")
        if not curator:
            self.stdout.write(f"{entry['dbase_number']}: No curators for {entry['dbase_number']}")
            return result
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
            self.stderr.write(f"{entry['dbase_number']}: Cannot create curator {curator}")
        else:
            result.append(curator_entry)
            if curator_created:
                curator_entry.save()
                self.stdout.write(f"{entry['dbase_number']}: Added curator {curator} with id { curator_entry.id }")
            else:
                self.stdout.write(f"{entry['dbase_number']}: Reusing curator {curator}")
        return result

    def add_donors(self, entry: dict[str, Any]) -> list[Donor]:
        """Return donor objects from an entry."""
        result: list[Donor] = []
        donors = entry.get("donors", [])
        if not donors:
            self.stdout.write(f"{entry['dbase_number']}: No donors for {entry['dbase_number']}")
            return result
        for donor in donors:
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
                self.stderr.write(f"{entry['dbase_number']}: Cannot create donor {donor}")
            else:
                result.append(donor_entry)
                if donor_created:
                    donor_entry.save()
                    self.stdout.write(f"{entry['dbase_number']}: Added donor {donor} with id { donor_entry.id }")
                else:
                    self.stdout.write(f"{entry['dbase_number']}: Reusing donor {donor}")
        return result

    def add_editor(self, entry: dict[str, Any]) -> Optional[Editor]:
        """Return editor objects from an entry."""
        editor_place = entry.get("editor")
        if not editor_place:
            return None
        editor = editor_place.split(" // ")[0]
        if editor == "None":
            editor = None
        place = editor_place.split(" // ")[1]
        if place == "None":
            place = None
        editor_entry, editor_created = Editor.objects.get_or_create(
            name=editor,
            place=place,
        )
        if not editor_entry:
            self.stderr.write(f"{entry['dbase_number']}: Cannot create editor {editor} {place}")
        else:
            if editor_created:
                editor_entry.save()
                self.stdout.write(f"{entry['dbase_number']}: Added editor {editor} {place} with id { editor_entry.id }")
            else:
                self.stdout.write(f"{entry['dbase_number']}: Reusing editor {editor} {place}")
        return editor_entry

    def add_topics(self, entry: dict[str, Any]) -> list[Topic]:
        """Return topic objects from an entry."""
        result: list[Topic] = []
        topic_list = entry.get("topics", [])
        for topic in topic_list:
            topic_entry, topic_created = Topic.objects.get_or_create(
                topic_name=topic,
            )
            if not topic_entry:
                self.stderr.write(f"{entry['dbase_number']}: Cannot create topic {topic}")
            else:
                result.append(topic_entry)
                if topic_created:
                    topic_entry.save()
                    self.stdout.write(f"{entry['dbase_number']}: Added topic {topic} with id { topic_entry.id }")
                else:
                    self.stdout.write(f"{entry['dbase_number']}: Reusing topic {topic}")
        return result

    def add_original_entry(
        self,
        entry: dict[str, Any],
        book_entry,
        import_time,
    ) -> DbfEntry:
        """Return a dbf entry object from a converted entry."""
        # Original DBF Entry
        dbf_entry, entry_created = DbfEntry.objects.get_or_create(
            dbf_sequence=entry["dbase_number"],
            defaults={
                "book_entry": book_entry,
                "import_time": import_time,
            },
        )

        # Original DBF Rows
        for k, v in entry["original_entry"].items():
            if v:
                DbfEntryRow.objects.get_or_create(
                    dbfentry=dbf_entry,
                    code=k,
                    defaults={"value": v},
                )
        if not dbf_entry:
            self.stderr.write(f"{entry['dbase_number']}: Cannot create original dbf entry")
        else:
            if entry_created:
                dbf_entry.save()
                self.stdout.write(f"{entry['dbase_number']}: Added original dbf entry with id { dbf_entry.id }")
            else:
                self.stderr.write(f"{entry['dbase_number']}: Reusing original dbf entry????")
        return dbf_entry

    def add_book_entry(
        self,
        entry: dict[str, Any],
        authors,
        translators,
        curators,
        donors,
        editor,
        topics,
    ) -> BookEntry:
        """Return a complete book object from an entry."""
        title = entry.get("title")
        subtitle = entry.get("subtitle")
        dewey = entry.get("dewey")
        language = entry.get("language")
        edition = entry.get("edition")
        edition_year = entry.get("edition_year")
        pages = entry.get("pages")
        copies = entry.get("copies")
        volume = entry.get("volume")
        material = entry.get("material")
        notes = entry.get("notes")
        isbn = entry.get("isbn")
        issn = entry.get("issn")
        ean = entry.get("ean")
        has_cd = entry.get("has_cd")
        has_dvd = entry.get("has_dvd")
        is_offprint = entry.get("offprint")

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
            self.stderr.write(f"{entry['dbase_number']}: Cannot create book entry")
        else:
            if entry_created:
                book_entry.authors.set(authors)
                book_entry.translators.set(translators)
                book_entry.curators.set(curators)
                book_entry.topics.set(topics)
                book_entry.entry_donors.set(donors)
                book_entry.save()
                self.stdout.write(f"{entry['dbase_number']}: Added book entry")
            else:
                self.stderr.write(
                    f"{entry['dbase_number']}: Reusing book entry. "
                    f"Previous sequence { book_entry.dbf_sequence() }: {book_entry}"
                )
        return book_entry

    def add_entry_numbers(self, entry, book_entry, donors):
        """Add entry numbers to books."""
        entry_numbers = entry.get("entry_numbers")
        copies = entry.get("copies")

        if not entry_numbers:
            return
        for entry_number in entry_numbers:
            entry_number_object, entry_created = EntryNumber.objects.get_or_create(
                entry_number=entry_number,
                defaults={
                    "book_entry": book_entry,
                },
            )
            if not entry_number_object:
                self.stderr.write(f"{entry['dbase_number']}: Cannot create entry number for {entry_number}")
            else:
                if not entry_created:
                    previous_book_entry = entry_number_object.book_entry
                    self.stderr.write(
                        f"{entry['dbase_number']}: entry number {entry_number} is already"
                        f" used by { previous_book_entry.dbf_sequence() }:{previous_book_entry}."
                        f" Replacing with {entry['dbase_number']}:{book_entry}"
                    )
                entry_number_object.copies = copies
                entry_number_object.book_entry = book_entry
                entry_number_object.save()
                entry_number_object.entry_number_donors.set(donors)
                self.stdout.write(f"{entry['dbase_number']}: Added entry number {entry_number}")

    def add_arguments(self, parser):
        """Handle entries argument."""
        parser.add_argument("entries")

    def handle(self, *args, **options):
        """Read a yaml file with entries and add to database."""
        usr = User.objects.get(username="rockdreamer@gmail.com")
        usr.set_password(os.environ.get("DJANGO_ADMIN_INITIAL_PASSWORD", "admin"))
        usr.save()
        all_entries = read_all_entries(entries_file=options["entries"])
        start_time = datetime.datetime.utcnow()
        for entry in all_entries:
            if entry_is_empty(entry):
                self.stdout.write(f"\n---- EMPTY: {entry['dbase_number']} ----")
                self.add_original_entry(
                    entry,
                    None,
                    start_time,
                )
            else:
                self.stdout.write(f"\n---- {entry['dbase_number']} ----")
                authors = self.add_authors(entry)
                translators = self.add_translators(entry)
                curators = self.add_curator(entry)
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
                self.add_entry_numbers(entry=entry, book_entry=book_entry, donors=donors)

                self.add_original_entry(
                    entry,
                    book_entry,
                    start_time,
                )
        print(f"Inserted {len(all_entries)} entries in {(datetime.datetime.now()-start_time).seconds}s", flush=True)
