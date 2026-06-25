"""Data-access layer for curation workflows."""

from django.db import connection

from books.models import Author
from books.models import BookEntry
from curation.models import SuppressedPair

DEFAULT_SIMILARITY_THRESHOLD = 0.6

# Scalar fields on BookEntry that may conflict between two duplicate entries.
# Booleans are excluded (handled with True-wins logic automatically).
BOOK_SCALAR_FIELDS = [
    "title",
    "subtitle",
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
    "editor_id",
]
BOOK_BOOLEAN_FIELDS = ["offprint", "has_cd", "has_dvd"]


def _pair_query(table, column, exclude_suppressed=False):
    suppression_clause = (
        """
          AND NOT EXISTS (
            SELECT 1 FROM curation_suppressedpair sp
            WHERE sp.content_type_id = %s
              AND sp.object_a_id = a.id
              AND sp.object_b_id = b.id
          )"""
        if exclude_suppressed
        else ""
    )
    return f"""
        SELECT
            a.id AS a_id,
            b.id AS b_id,
            similarity(a.{column}, b.{column}) AS sim
        FROM {table} a
        JOIN {table} b ON a.id < b.id AND a.{column} %% b.{column}
        WHERE a.{column} <> ''
          AND b.{column} <> ''{suppression_clause}
        ORDER BY sim DESC
        LIMIT 200
    """


def _fetch_pairs(sql, threshold, model_class, include_suppressed, prefetch=None):
    """Execute a self-join similarity query and return enriched pair dicts."""
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(model_class)
    sql_params = [] if include_suppressed else [ct.pk]

    with connection.cursor() as cursor:
        # SET LOCAL makes % operator use our threshold for the duration of this query.
        # The GiST trigram index can then accelerate the join via index nested loop.
        cursor.execute("SET LOCAL pg_trgm.similarity_threshold = %s", [threshold])
        cursor.execute(sql, sql_params)
        rows = cursor.fetchall()

    if not rows:
        return []

    all_ids = list({r[0] for r in rows} | {r[1] for r in rows})
    qs = model_class.objects.filter(pk__in=all_ids)
    if prefetch:
        qs = qs.prefetch_related(*prefetch)
    objects_by_id = {obj.pk: obj for obj in qs}

    pairs = []
    for a_id, b_id, sim in rows:
        if a_id not in objects_by_id or b_id not in objects_by_id:
            continue
        pairs.append(
            {
                "object_a": objects_by_id[a_id],
                "object_b": objects_by_id[b_id],
                "similarity": round(sim, 3),
            }
        )
    return pairs


def get_duplicate_author_pairs(threshold, include_suppressed=False):
    """Return similar Author pairs above the given pg_trgm threshold."""
    sql = _pair_query("books_author", "romanized_name", exclude_suppressed=not include_suppressed)
    return _fetch_pairs(sql, threshold, Author, include_suppressed, prefetch=["bookentry_set"])


def get_duplicate_book_pairs(threshold, include_suppressed=False):
    """Return similar BookEntry pairs above the given pg_trgm threshold."""
    sql = _pair_query("books_bookentry", "romanized_title", exclude_suppressed=not include_suppressed)
    return _fetch_pairs(sql, threshold, BookEntry, include_suppressed, prefetch=["authors", "entrynumber_set"])
