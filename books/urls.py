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
]
