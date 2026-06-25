from django.contrib import admin

from curation.models import MergeLog
from curation.models import SuppressedPair


@admin.register(SuppressedPair)
class SuppressedPairAdmin(admin.ModelAdmin):
    list_display = ["content_type", "object_a", "object_b", "suppressed_by", "suppressed_at"]
    list_filter = ["content_type", "suppressed_by"]
    readonly_fields = [
        "content_type",
        "object_a_id",
        "object_b_id",
        "object_a",
        "object_b",
        "suppressed_by",
        "suppressed_at",
    ]
    ordering = ["-suppressed_at"]

    def object_a(self, obj):
        return str(obj.object_a) if obj.object_a else f"(deleted id={obj.object_a_id})"

    def object_b(self, obj):
        return str(obj.object_b) if obj.object_b else f"(deleted id={obj.object_b_id})"


@admin.register(MergeLog)
class MergeLogAdmin(admin.ModelAdmin):
    list_display = ["content_type", "target_object", "merged_by", "merged_at", "undone_at"]
    list_filter = ["content_type", "merged_by"]
    readonly_fields = [
        "content_type",
        "target_object_id",
        "target_object",
        "merge_data",
        "merged_by",
        "merged_at",
        "undone_at",
        "undone_by",
    ]
    ordering = ["-merged_at"]

    def target_object(self, obj):
        return str(obj.target_object) if obj.target_object else f"(deleted id={obj.target_object_id})"
