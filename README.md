# Skoufas Library

Web application for managing the library catalog of the Skoufas Association (Σύλλογος Σκουφάς) in Arta, Greece - a cultural association founded in 1896 whose library dates back to the same year.

**Live site:** https://library.skoufas.gr

## Features

**Books** - Catalog books with authors, translators, curators, topics, editors, and donors; track physical copies via entry numbers and a building/room/shelf/box location hierarchy; Greek full-text search; cover image upload or fetch from OpenLibrary/Google Books; export to CSV or MARC 21 (ISO 2709, MARCXML, MARCMaker).

**Loaning** - A circulation desk for checking books in and out, tracking active/overdue/closed loans, and managing borrower records.

**Curation** - Data-quality tools: detect and merge duplicate authors/books/editors/translators/curators/topics (with full undo history), and conduct physical shelf/box inventory sessions.

## Built with

Django, PostgreSQL, django-bootstrap5, django-watson (full-text search), DjangoQL (advanced admin search), pymarc (MARC 21 export), django-imagekit.

## CLI

The project installs a `skoufas-library` command (see `skoufas_library_project/cli.py`) that wraps Django's management commands, e.g. `skoufas-library migrate`.

## Setup

### Dev container (recommended)

Open the repo in VS Code or GitHub Codespaces with the Dev Containers extension. `.devcontainer/` provisions the app and a PostgreSQL database automatically, forwards port 8000, and runs `scripts/restart-venv` on start.

### Manual setup

```
./scripts/restart-venv   # creates .venv and installs the project with test/lint extras via uv
```

Requires a running PostgreSQL instance - see `skoufas_library_project/settings.py` for the expected `DJANGO_DATABASE_*` environment variables.

## License

[GNU Affero General Public License v3.0](LICENSE)
