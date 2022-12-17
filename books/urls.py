"""Book related URLs."""
from django.urls import path
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

from books import views

app_name = "books"
urlpatterns: list[URLPattern | URLResolver] = [
    path(r"", views.BookEntryListView.as_view(), name="book-list"),
    path(r"by-db-id/<int:pk>", views.BookEntryDetailView.as_view(), name="book-by-id"),
    path(r"by-entry-number/<int:pk>", views.BookEntryByEntryNumberDetailView.as_view(), name="book-by-entry-number"),
]
