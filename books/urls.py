"""Book related URLs."""
from django.urls import path
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

from books import views

app_name = "books"  # pylint: disable=invalid-name
urlpatterns: list[URLPattern | URLResolver] = [
    path(r"", views.BookEntryListView.as_view(), name="book-list"),
    path(r"by-db-id/<int:pk>", views.BookEntryDetailView.as_view(), name="book-by-id"),
    path(r"by-entry-number/<int:pk>", views.BookEntryByEntryNumberDetailView.as_view(), name="book-by-entry-number"),
    path(r"authors", views.AuthorListView.as_view(), name="author-list"),
    path(r"authors/by-db-id/<int:pk>", views.AuthorDetailView.as_view(), name="author-by-id"),
    path(r"donors", views.DonorListView.as_view(), name="donor-list"),
    path(r"donors/by-db-id/<int:pk>", views.DonorDetailView.as_view(), name="donor-by-id"),
    path(r"classes", views.ClassListView.as_view(), name="skoufas-class-list"),
    path(
        r"by-skoufas-main-class/<classification_class>",
        views.BookEntryByMainClassListView.as_view(),
        name="book-by-skoufas-main-class",
    ),
    path(
        r"by-skoufas-classification/<skoufas_classification>",
        views.BookEntryBySkoufasClassificationListView.as_view(),
        name="book-by-skoufas-classification",
    ),
    path(
        r"export/csv",
        views.CSVExportView.as_view(),
        name="export-csv",
    ),
]
