"""Curation views for author and book deduplication workflows.

Split by concern: duplicates.py (author/book/translator/curator/topic/editor
duplicate detection & merge), merge_log.py (merge log + undo), suppression.py,
inventory.py. Re-exported here so ``from curation import views`` keeps
working unchanged.
"""

from curation.views.duplicates import AuthorDuplicatesView
from curation.views.duplicates import AuthorMergeReviewView
from curation.views.duplicates import BookDuplicatesView
from curation.views.duplicates import BookMergeReviewView
from curation.views.duplicates import CuratorDuplicatesView
from curation.views.duplicates import CuratorMergeReviewView
from curation.views.duplicates import EditorDuplicatesView
from curation.views.duplicates import EditorMergeReviewView
from curation.views.duplicates import TopicDuplicatesView
from curation.views.duplicates import TopicMergeReviewView
from curation.views.duplicates import TranslatorDuplicatesView
from curation.views.duplicates import TranslatorMergeReviewView
from curation.views.inventory import InventorySessionCloseView
from curation.views.inventory import InventorySessionConfirmView
from curation.views.inventory import InventorySessionListView
from curation.views.inventory import InventorySessionScanView
from curation.views.inventory import InventorySessionSetAsideView
from curation.views.merge_log import MergeLogListView
from curation.views.merge_log import MergeUndoView
from curation.views.suppression import SuppressedPairUnsuppressView

__all__ = [
    "AuthorDuplicatesView",
    "AuthorMergeReviewView",
    "BookDuplicatesView",
    "BookMergeReviewView",
    "CuratorDuplicatesView",
    "CuratorMergeReviewView",
    "EditorDuplicatesView",
    "EditorMergeReviewView",
    "InventorySessionCloseView",
    "InventorySessionConfirmView",
    "InventorySessionListView",
    "InventorySessionScanView",
    "InventorySessionSetAsideView",
    "MergeLogListView",
    "MergeUndoView",
    "SuppressedPairUnsuppressView",
    "TopicDuplicatesView",
    "TopicMergeReviewView",
    "TranslatorDuplicatesView",
    "TranslatorMergeReviewView",
]
