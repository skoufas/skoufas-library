"""Fetch cover images from Google Books / OpenLibrary for books that have no images."""

import mimetypes
import time
from typing import Any

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Count

from books.cover_fetcher import fetch_cover
from books.models import BookEntry
from books.models import BookEntryImage


class Command(BaseCommand):
    """Fetch cover images for books without images."""

    help = "Fetch cover images from Google Books / OpenLibrary for books that have no images"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            metavar="SECONDS",
            help="Seconds to wait between requests (default: 1.0)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        delay: float = options["delay"]

        all_without_images = BookEntry.objects.annotate(image_count=Count("images")).filter(image_count=0)

        # Books with a usable ISBN
        with_isbn = all_without_images.exclude(isbn="").exclude(isbn__isnull=True)
        isbn_pks = set(with_isbn.values_list("pk", flat=True))

        # Books without ISBN but with a book EAN (978/979)
        with_ean_only = (
            (all_without_images.filter(isbn__isnull=True) | all_without_images.filter(isbn=""))
            .exclude(ean__isnull=True)
            .exclude(ean="")
            .exclude(pk__in=isbn_pks)
        )
        with_ean_only = with_ean_only.filter(ean__startswith="978") | with_ean_only.filter(ean__startswith="979")

        # Books with neither
        no_identifier = (
            all_without_images.exclude(pk__in=isbn_pks)
            .exclude(pk__in=with_ean_only.values_list("pk", flat=True))
            .count()
        )

        candidates = (with_isbn | with_ean_only).distinct()
        total = candidates.count()

        self.stdout.write(
            f"Books without images: {total} searchable (ISBN or book EAN), {no_identifier} without any identifier (skipped)\n"
        )

        fetched = 0
        not_found = 0

        for book in candidates.order_by("pk").iterator():
            isbn = book.isbn or ""
            ean = book.ean or ""
            identifier = isbn or ean
            id_label = "ISBN" if isbn else "EAN"

            result = fetch_cover(isbn=isbn, ean=ean)
            if result:
                ext = mimetypes.guess_extension(result.content_type) or ".jpg"
                if ext in (".jpe", ".jfif"):
                    ext = ".jpg"
                filename = f"cover_{identifier}{ext}"
                BookEntryImage.objects.create(
                    book_entry=book,
                    image=ContentFile(result.image_bytes, name=filename),
                    image_type=BookEntryImage.ImageType.COVER,
                    caption=f"Fetched from {result.source} ({id_label}: {identifier})",
                    order=0,
                )
                fetched += 1
                self.stdout.write(f"  [OK] {book.pk}: {book.title[:60]} ({result.source})")
            else:
                not_found += 1
                self.stdout.write(f"  [--] {book.pk}: {book.title[:60]} (not found)")

            if delay > 0:
                time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Fetched: {fetched}, Not found: {not_found}, Skipped (no identifier): {no_identifier}"
            )
        )
