"""Curation URL configuration."""

from django.urls import path
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

from curation import views

app_name = "curation"  # pylint: disable=invalid-name
urlpatterns: list[URLPattern | URLResolver] = [
    path("authors/duplicates/", views.AuthorDuplicatesView.as_view(), name="author-duplicates"),
    path("authors/merge/<int:a_id>/<int:b_id>/", views.AuthorMergeReviewView.as_view(), name="author-merge-review"),
    path("authors/undo/<int:log_id>/", views.AuthorMergeUndoView.as_view(), name="author-merge-undo"),
    path("books/duplicates/", views.BookDuplicatesView.as_view(), name="book-duplicates"),
    path("books/merge/<int:a_id>/<int:b_id>/", views.BookMergeReviewView.as_view(), name="book-merge-review"),
    path("books/undo/<int:log_id>/", views.BookMergeUndoView.as_view(), name="book-merge-undo"),
    path("merges/", views.MergeLogListView.as_view(), name="merge-log-list"),
    path("suppressed/<int:pair_id>/unsuppress/", views.SuppressedPairUnsuppressView.as_view(), name="unsuppress-pair"),
]
