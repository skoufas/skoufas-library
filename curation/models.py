"""Curation models: SuppressedPair and MergeLog."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SuppressedPair(models.Model):
    """A pair of same-type objects that a curator has dismissed as not being duplicates."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("content type"))
    object_a_id = models.PositiveIntegerField(verbose_name=_("object A ID"))
    object_b_id = models.PositiveIntegerField(verbose_name=_("object B ID"))
    object_a = GenericForeignKey("content_type", "object_a_id")
    object_b = GenericForeignKey("content_type", "object_b_id")
    suppressed_by = models.ForeignKey(User, verbose_name=_("suppressed by"), null=True, on_delete=models.SET_NULL)
    suppressed_at = models.DateTimeField(verbose_name=_("suppressed at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Suppressed pair")
        verbose_name_plural = _("Suppressed pairs")
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_a_id", "object_b_id"],
                name="unique_suppressed_pair",
            )
        ]

    def __str__(self):
        return f"{self.object_a} / {self.object_b}"


class MergeLog(models.Model):
    """Audit record of a merge operation, storing enough data to undo it."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("content type"))
    target_object_id = models.PositiveIntegerField(verbose_name=_("target object ID"), null=True)
    target_object = GenericForeignKey("content_type", "target_object_id")
    merge_data = models.JSONField(
        verbose_name=_("merge data"),
        help_text=_("Entity-specific snapshot of the deleted source object and all data needed to undo the merge."),
    )
    merged_by = models.ForeignKey(
        User, verbose_name=_("merged by"), null=True, on_delete=models.SET_NULL, related_name="merges_performed"
    )
    merged_at = models.DateTimeField(verbose_name=_("merged at"), auto_now_add=True)
    undone_at = models.DateTimeField(verbose_name=_("undone at"), null=True, blank=True)
    undone_by = models.ForeignKey(
        User,
        verbose_name=_("undone by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="merges_undone",
    )

    class Meta:
        verbose_name = _("Merge log")
        verbose_name_plural = _("Merge logs")
        ordering = ["-merged_at"]
        permissions = [
            ("can_curate", "Can curate catalog"),
        ]

    def __str__(self):
        source_name = self.merge_data.get("source_display", "?")
        target_name = str(self.target_object) if self.target_object else "?"
        return f"{source_name} → {target_name}"

    @property
    def is_undone(self):
        return self.undone_at is not None

    @property
    def can_undo(self):
        if self.is_undone or not self.target_object_id:
            return False
        try:
            return self.content_type.get_object_for_this_type(pk=self.target_object_id) is not None
        except Exception:
            return False


class InventorySession(models.Model):
    """A physical inventory session for a single leaf location (Shelf or Box)."""

    location = models.ForeignKey(
        "books.Location",
        verbose_name=_("location"),
        on_delete=models.PROTECT,
        related_name="inventory_sessions",
    )
    started_by = models.ForeignKey(
        User, verbose_name=_("started by"), null=True, on_delete=models.SET_NULL, related_name="inventory_sessions"
    )
    started_at = models.DateTimeField(verbose_name=_("started at"), auto_now_add=True)
    closed_at = models.DateTimeField(verbose_name=_("closed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("Inventory session")
        verbose_name_plural = _("Inventory sessions")
        ordering = ["-started_at"]
        permissions = [
            ("can_inventory", "Can perform inventory"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["location"],
                condition=models.Q(closed_at=None),
                name="unique_open_inventory_session_per_location",
            )
        ]

    def __str__(self):
        return f"{self.location} @ {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def is_open(self):
        return self.closed_at is None


class InventorySessionEntry(models.Model):
    """A single scanned entry number within an inventory session."""

    OUTCOME_CONFIRMED = "confirmed"
    OUTCOME_SET_ASIDE = "set_aside"
    OUTCOME_CHOICES = [
        (OUTCOME_CONFIRMED, _("Confirmed")),
        (OUTCOME_SET_ASIDE, _("Set aside")),
    ]

    session = models.ForeignKey(
        InventorySession,
        verbose_name=_("session"),
        on_delete=models.CASCADE,
        related_name="entries",
    )
    entry_number = models.ForeignKey(
        "books.EntryNumber",
        verbose_name=_("entry number"),
        on_delete=models.PROTECT,
        related_name="inventory_entries",
    )
    scanned_at = models.DateTimeField(verbose_name=_("scanned at"), auto_now_add=True)
    outcome = models.CharField(verbose_name=_("outcome"), max_length=20, choices=OUTCOME_CHOICES)
    previous_location = models.ForeignKey(
        "books.Location",
        verbose_name=_("previous location"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_entries_from",
    )

    class Meta:
        verbose_name = _("Inventory session entry")
        verbose_name_plural = _("Inventory session entries")
        ordering = ["scanned_at"]

    def __str__(self):
        return f"{self.entry_number} ({self.get_outcome_display()})"
