"""Physical inventory workflow: sessions, scanning, confirmation, and close-out."""

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import TemplateResponseMixin

from books.models import EntryNumber, Location
from curation.models import InventorySession, InventorySessionEntry

_LEAF_TYPES = {Location.TYPE_SHELF, Location.TYPE_BOX}
_PENDING_KEY = "inventory_pending_entry_number_id"
_PENDING_CONFLICT = "inventory_pending_conflict"


class InventorySessionListView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Hub: list open sessions and allow starting a new one."""

    permission_required = "curation.can_inventory"
    template_name = "curation/inventory_session_list.html"

    def get(self, request):
        """List open and recently-closed inventory sessions, and leaf locations to start one."""
        open_sessions = InventorySession.objects.filter(closed_at=None).select_related("location", "started_by")
        recent_closed = InventorySession.objects.exclude(closed_at=None).select_related("location", "started_by")[:10]
        leaf_locations = Location.objects.filter(type__in=_LEAF_TYPES).order_by("name")
        return self.render_to_response(
            {"open_sessions": open_sessions, "recent_closed": recent_closed, "leaf_locations": leaf_locations}
        )

    def post(self, request):
        """Start a new inventory session for the selected leaf location."""
        location_id = request.POST.get("location_id")
        location = get_object_or_404(Location, pk=location_id)
        if location.type not in _LEAF_TYPES:
            messages.error(request, _("Only Shelf or Box locations can be inventoried."))
            return redirect("curation:inventory-list")
        try:
            session = InventorySession.objects.create(location=location, started_by=request.user)
        except IntegrityError:
            existing = InventorySession.objects.get(location=location, closed_at=None)
            messages.error(
                request,
                _("An open inventory session already exists for this location."),
            )
            return redirect("curation:inventory-scan", pk=existing.pk)
        return redirect("curation:inventory-scan", pk=session.pk)


class InventorySessionScanView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Scan screen: show scan input and handle pending confirmation."""

    permission_required = "curation.can_inventory"
    template_name = "curation/inventory_scan.html"

    def _session(self, pk):
        return get_object_or_404(InventorySession, pk=pk, closed_at=None)

    def _pending_context(self, request):
        """Return context dict for the pending entry review, or empty dict."""
        en_id = request.session.get(_PENDING_KEY)
        if not en_id:
            return {}
        try:
            en = EntryNumber.objects.select_related("book_entry", "location").get(pk=en_id)
        except EntryNumber.DoesNotExist:
            request.session.pop(_PENDING_KEY, None)
            request.session.pop(_PENDING_CONFLICT, None)
            return {}
        return {
            "pending": en,
            "pending_conflict": request.session.get(_PENDING_CONFLICT, False),
        }

    def get(self, request, pk):
        """Show the scan input, recent scans, and any pending confirmation."""
        session = self._session(pk)
        recent = session.entries.select_related("entry_number__book_entry").order_by("-scanned_at")[:10]
        ctx = {"session": session, "recent_entries": recent}
        ctx.update(self._pending_context(request))
        return self.render_to_response(ctx)

    def post(self, request, pk):
        """Look up the scanned entry number and stash it as pending confirmation."""
        session = self._session(pk)
        entry_number_value = request.POST.get("entry_number", "").strip()
        if not entry_number_value:
            messages.error(request, _("Please enter an entry number."))
            return redirect("curation:inventory-scan", pk=pk)

        try:
            en = (
                EntryNumber.objects.select_related("book_entry", "location")
                .prefetch_related("book_entry__authors")
                .get(entry_number=int(entry_number_value))
            )
        except EntryNumber.DoesNotExist, ValueError:
            messages.error(request, _('Entry number "%(en)s" not found in the database.') % {"en": entry_number_value})
            return redirect("curation:inventory-scan", pk=pk)

        conflict = en.location_id is not None and en.location_id != session.location_id
        request.session[_PENDING_KEY] = en.pk
        request.session[_PENDING_CONFLICT] = conflict
        return redirect("curation:inventory-scan", pk=pk)


class InventorySessionConfirmView(PermissionRequiredMixin, View):
    """Confirm scanned entry: assign location and record the session entry."""

    permission_required = "curation.can_inventory"

    def post(self, request, pk):
        """Assign the pending entry number to this session's location."""
        session = get_object_or_404(InventorySession, pk=pk, closed_at=None)
        en_id = request.session.get(_PENDING_KEY)
        if not en_id:
            messages.error(request, _("No pending scan to confirm."))
            return redirect("curation:inventory-scan", pk=pk)

        en = get_object_or_404(EntryNumber, pk=en_id)
        with transaction.atomic():
            previous_location = en.location
            en.location = session.location
            en.save(update_fields=["location"])
            InventorySessionEntry.objects.create(
                session=session,
                entry_number=en,
                outcome=InventorySessionEntry.OUTCOME_CONFIRMED,
                previous_location=previous_location if previous_location != session.location else None,
            )

        request.session.pop(_PENDING_KEY, None)
        request.session.pop(_PENDING_CONFLICT, None)
        messages.success(
            request,
            _("%(en)s confirmed and assigned to %(loc)s.") % {"en": en.entry_number, "loc": session.location},
        )
        return redirect("curation:inventory-scan", pk=pk)


class InventorySessionSetAsideView(PermissionRequiredMixin, View):
    """Set aside a scanned entry: flag it without changing its location."""

    permission_required = "curation.can_inventory"

    def post(self, request, pk):
        """Flag the pending entry number as set aside, without changing its location."""
        session = get_object_or_404(InventorySession, pk=pk, closed_at=None)
        en_id = request.session.get(_PENDING_KEY)
        if not en_id:
            messages.error(request, _("No pending scan to set aside."))
            return redirect("curation:inventory-scan", pk=pk)

        en = get_object_or_404(EntryNumber, pk=en_id)
        InventorySessionEntry.objects.create(
            session=session,
            entry_number=en,
            outcome=InventorySessionEntry.OUTCOME_SET_ASIDE,
            previous_location=en.location,
        )
        request.session.pop(_PENDING_KEY, None)
        request.session.pop(_PENDING_CONFLICT, None)
        messages.warning(
            request,
            _("%(en)s set aside for entry number reassignment.") % {"en": en.entry_number},
        )
        return redirect("curation:inventory-scan", pk=pk)


class InventorySessionCloseView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Reconciliation report + close the session."""

    permission_required = "curation.can_inventory"
    template_name = "curation/inventory_close.html"

    def _reconciliation(self, session):
        scanned_ids = set(session.entries.values_list("entry_number_id", flat=True))
        expected = EntryNumber.objects.filter(location=session.location).select_related("book_entry")
        expected_ids = set(expected.values_list("pk", flat=True))
        missing_ids = expected_ids - scanned_ids

        confirmed = session.entries.filter(outcome=InventorySessionEntry.OUTCOME_CONFIRMED).select_related(
            "entry_number__book_entry", "previous_location"
        )
        set_aside = session.entries.filter(outcome=InventorySessionEntry.OUTCOME_SET_ASIDE).select_related(
            "entry_number__book_entry", "previous_location"
        )
        missing = EntryNumber.objects.filter(pk__in=missing_ids).select_related("book_entry")

        return {
            "confirmed": confirmed,
            "set_aside": set_aside,
            "missing": missing,
            "confirmed_count": confirmed.count(),
            "set_aside_count": set_aside.count(),
            "missing_count": len(missing_ids),
        }

    def get(self, request, pk):
        """Show the reconciliation report (confirmed / set aside / missing)."""
        session = get_object_or_404(InventorySession, pk=pk)
        ctx = {"session": session, "read_only": session.closed_at is not None}
        ctx.update(self._reconciliation(session))
        return self.render_to_response(ctx)

    def post(self, request, pk):
        """Close the inventory session."""
        session = get_object_or_404(InventorySession, pk=pk, closed_at=None)
        session.closed_at = timezone.now()
        session.save(update_fields=["closed_at"])
        messages.success(request, _("Inventory session for %(loc)s closed.") % {"loc": session.location})
        return redirect("curation:inventory-list")
