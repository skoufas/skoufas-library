"""Views on Books."""
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    """Home page."""

    template_name = "home.html"
