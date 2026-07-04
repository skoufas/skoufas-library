"""Views for browsing the building/room/shelf/box location hierarchy."""

from django.core.exceptions import PermissionDenied
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from books.models import EntryNumber, Location
from curation.models import InventorySession


class LocationListView(ListView):
    """List top-level locations (buildings)."""

    model = Location
    template_name = "books/location_list.html"

    def get_queryset(self):
        """Return buildings only, filtering out non-public ones for unpermitted users."""
        qs = Location.objects.filter(parent__isnull=True)
        if not self.request.user.has_perm("books.view_nonpublic_location"):
            qs = qs.filter(non_public=False)
        return qs


class LocationDetailView(DetailView):
    """Detail view for a single location node."""

    model = Location
    template_name = "books/location_detail.html"

    def get_object(self, queryset=None):
        """Return the location, raising PermissionDenied if non-public and not permitted."""
        obj = super().get_object(queryset)
        if not obj.is_accessible(self.request.user):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        """Add children and descendant entry numbers to context."""
        context = super().get_context_data(**kwargs)
        location = context["object"]
        user = self.request.user
        can_see_nonpublic = user.has_perm("books.view_nonpublic_location")

        # Ancestor chain for breadcrumb (root first)
        ancestors = []
        node = location.parent
        while node is not None:
            ancestors.insert(0, node)
            node = node.parent if node.parent_id else None
        context["ancestors"] = ancestors

        # Direct children — filter non-public if needed
        children_qs = location.children.all()
        if not can_see_nonpublic:
            children_qs = children_qs.filter(non_public=False)
        context["children"] = children_qs

        # Entry numbers at this node and all descendants
        descendant_ids = location.get_descendant_ids()
        all_location_ids = [location.pk] + descendant_ids
        context["entry_numbers"] = (
            EntryNumber.objects.filter(location_id__in=all_location_ids)
            .select_related("book_entry", "location")
            .order_by("entry_number")
        )

        # Inventory session button (only for leaf locations)
        if location.type in {Location.TYPE_SHELF, Location.TYPE_BOX}:
            context["open_inventory_session"] = InventorySession.objects.filter(
                location=location, closed_at=None
            ).first()
            context["is_leaf_location"] = True
        return context
