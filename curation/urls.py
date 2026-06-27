"""Curation URL configuration."""

from django.urls import path
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

from curation import views

app_name = "curation"  # pylint: disable=invalid-name
urlpatterns: list[URLPattern | URLResolver] = [
    path("authors/duplicates/", views.AuthorDuplicatesView.as_view(), name="author-duplicates"),
    path("authors/merge/<int:a_id>/<int:b_id>/", views.AuthorMergeReviewView.as_view(), name="author-merge-review"),
    path("books/duplicates/", views.BookDuplicatesView.as_view(), name="book-duplicates"),
    path("books/merge/<int:a_id>/<int:b_id>/", views.BookMergeReviewView.as_view(), name="book-merge-review"),
    path("curators/duplicates/", views.CuratorDuplicatesView.as_view(), name="curator-duplicates"),
    path("curators/merge/<int:a_id>/<int:b_id>/", views.CuratorMergeReviewView.as_view(), name="curator-merge-review"),
    path("editors/duplicates/", views.EditorDuplicatesView.as_view(), name="editor-duplicates"),
    path("editors/merge/<int:a_id>/<int:b_id>/", views.EditorMergeReviewView.as_view(), name="editor-merge-review"),
    path("topics/duplicates/", views.TopicDuplicatesView.as_view(), name="topic-duplicates"),
    path("topics/merge/<int:a_id>/<int:b_id>/", views.TopicMergeReviewView.as_view(), name="topic-merge-review"),
    path("translators/duplicates/", views.TranslatorDuplicatesView.as_view(), name="translator-duplicates"),
    path(
        "translators/merge/<int:a_id>/<int:b_id>/",
        views.TranslatorMergeReviewView.as_view(),
        name="translator-merge-review",
    ),
    path("merges/", views.MergeLogListView.as_view(), name="merge-log-list"),
    path("merges/undo/<int:log_id>/", views.MergeUndoView.as_view(), name="merge-undo"),
    path("suppressed/<int:pair_id>/unsuppress/", views.SuppressedPairUnsuppressView.as_view(), name="unsuppress-pair"),
    # Inventory
    path("inventory/", views.InventorySessionListView.as_view(), name="inventory-list"),
    path("inventory/<int:pk>/", views.InventorySessionScanView.as_view(), name="inventory-scan"),
    path("inventory/<int:pk>/confirm/", views.InventorySessionConfirmView.as_view(), name="inventory-confirm"),
    path("inventory/<int:pk>/set-aside/", views.InventorySessionSetAsideView.as_view(), name="inventory-set-aside"),
    path("inventory/<int:pk>/close/", views.InventorySessionCloseView.as_view(), name="inventory-close"),
]
