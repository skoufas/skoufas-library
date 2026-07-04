"""Views on Books.

Split by concern: books.py (browse/detail/classification), people.py
(authors/donors), location.py, exports.py (CSV/MARC), images.py
(upload/fetch/convert/crop-detect). Re-exported here so ``from books import
views`` keeps working unchanged.
"""

from books.views.books import BookEntryByEntryNumberDetailView
from books.views.books import BookEntryByMainClassListView
from books.views.books import BookEntryBySkoufasClassificationListView
from books.views.books import BookEntryDetailView
from books.views.books import BookEntryListView
from books.views.books import ClassListView
from books.views.exports import CSVExportView
from books.views.exports import MARCExportView
from books.views.exports import MARCSingleBookDetailView
from books.views.exports import MARCSingleBookExportView
from books.views.images import BookEntryCoverDetectView
from books.views.images import BookEntryCoverFetchView
from books.views.images import BookEntryImageAddView
from books.views.images import BookEntryImageConvertView
from books.views.location import LocationDetailView
from books.views.location import LocationListView
from books.views.people import AuthorDetailView
from books.views.people import AuthorListView
from books.views.people import DonorDetailView
from books.views.people import DonorListView

__all__ = [
    "AuthorDetailView",
    "AuthorListView",
    "BookEntryByEntryNumberDetailView",
    "BookEntryByMainClassListView",
    "BookEntryBySkoufasClassificationListView",
    "BookEntryCoverDetectView",
    "BookEntryCoverFetchView",
    "BookEntryDetailView",
    "BookEntryImageAddView",
    "BookEntryImageConvertView",
    "BookEntryListView",
    "ClassListView",
    "CSVExportView",
    "DonorDetailView",
    "DonorListView",
    "LocationDetailView",
    "LocationListView",
    "MARCExportView",
    "MARCSingleBookDetailView",
    "MARCSingleBookExportView",
]
