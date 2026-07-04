"""Suppression (dismissed-pair) management views."""

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View

from curation.models import SuppressedPair


class SuppressedPairUnsuppressView(PermissionRequiredMixin, View):
    """Remove a suppression so the pair reappears in the duplicates list."""

    permission_required = "curation.can_curate"

    def post(self, request, pair_id):
        """Delete the suppression and redirect back to the relevant duplicates list."""
        pair = get_object_or_404(SuppressedPair, pk=pair_id)
        entity_type = pair.content_type.model
        pair.delete()
        messages.success(request, _("Dismissal removed. Pair will reappear in the duplicates list."))
        if entity_type == "bookentry":
            return redirect("curation:book-duplicates")
        if entity_type == "translator":
            return redirect("curation:translator-duplicates")
        if entity_type == "curator":
            return redirect("curation:curator-duplicates")
        if entity_type == "topic":
            return redirect("curation:topic-duplicates")
        if entity_type == "editor":
            return redirect("curation:editor-duplicates")
        return redirect("curation:author-duplicates")
