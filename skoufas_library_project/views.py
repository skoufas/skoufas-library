"""Views for top-level Skoufas Library project pages."""

import markdown
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import get_language
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

MANUAL_FALLBACK_LANGUAGE = "el"
MANUAL_DIR = settings.BASE_DIR / "docs"


IMAGE_STYLE = "max-width: 100%; height: auto; border: 1px solid #dee2e6; border-radius: 0.375rem;"


class _ResponsiveImageTreeprocessor(Treeprocessor):
    """Constrain and frame rendered images.

    Applied as an inline style rather than a CSS class so sizing is baked
    into the cached HTML itself, independent of the separately-cached
    stylesheet.
    """

    def run(self, root):
        """Set an inline style on every <img> in the tree."""
        for image in root.iter("img"):
            image.set("style", IMAGE_STYLE)


class _ResponsiveImageExtension(Extension):
    """Register the responsive-image treeprocessor with Python-Markdown."""

    def extendMarkdown(self, md):
        """Add the treeprocessor to the Markdown instance."""
        md.treeprocessors.register(_ResponsiveImageTreeprocessor(md), "responsive_images", 5)


MANUAL_MARKDOWN_EXTENSIONS: list[str | Extension] = ["extra", "toc", "sane_lists", _ResponsiveImageExtension()]


def _render_manual_html(language: str) -> str:
    """Render docs/manual.<language>.md to HTML, caching for the life of the process."""
    cache_key = f"manual-html-{language}"
    html = cache.get(cache_key)
    if html is not None:
        return html

    manual_path = MANUAL_DIR / f"manual.{language}.md"
    if not manual_path.exists():
        manual_path = MANUAL_DIR / f"manual.{MANUAL_FALLBACK_LANGUAGE}.md"

    html = markdown.markdown(
        manual_path.read_text(encoding="utf-8"),
        extensions=MANUAL_MARKDOWN_EXTENSIONS,
    )
    cache.set(cache_key, html, timeout=None)
    return html


def manual(request: HttpRequest) -> HttpResponse:
    """Render the staff manual, converted from Markdown on the fly."""
    html = _render_manual_html(get_language() or MANUAL_FALLBACK_LANGUAGE)
    return render(request, "skoufas_library/manual.html", {"manual_html": html})
