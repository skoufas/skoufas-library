"""Views for uploading, fetching, converting, and cropping book cover images."""

import base64
import io
import mimetypes
from dataclasses import dataclass

import numpy as np
import cv2
import pillow_heif
from PIL import Image

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from books.models import BookEntry, BookEntryImage


class BookEntryImageAddView(PermissionRequiredMixin, View):
    """Upload an image for a book entry."""

    permission_required = "curation.can_inventory"
    template_name = "books/bookentry_image_add.html"

    def _safe_next(self, request, fallback: str) -> str:
        """Return the next URL if it is safe, otherwise return the fallback."""
        next_url = request.POST.get("next") or request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return next_url
        return fallback

    def get(self, request, pk: int):
        """Show upload form."""
        book_entry = get_object_or_404(BookEntry, pk=pk)
        next_url = self._safe_next(request, book_entry.get_absolute_url())
        return render(
            request,
            self.template_name,
            {
                "book_entry": book_entry,
                "next_url": next_url,
                "image_type_choices": BookEntryImage.ImageType.choices,
            },
        )

    def post(self, request, pk: int):
        """Handle image upload."""
        book_entry = get_object_or_404(BookEntry, pk=pk)
        next_url = self._safe_next(request, book_entry.get_absolute_url())
        image_file = request.FILES.get("image")
        if image_file:
            pillow_heif.register_heif_opener()
            try:
                order = int(request.POST.get("order", 0))
            except ValueError, TypeError:
                order = 0
            image_type = request.POST.get("image_type", BookEntryImage.ImageType.COVER)
            if image_type not in BookEntryImage.ImageType.values:
                image_type = BookEntryImage.ImageType.COVER
            BookEntryImage.objects.create(
                book_entry=book_entry,
                image=image_file,
                image_type=image_type,
                caption=request.POST.get("caption", ""),
                order=order,
            )
        return redirect(next_url)


class BookEntryCoverFetchView(PermissionRequiredMixin, View):
    """Fetch a cover image from external providers and show a preview/confirm page."""

    permission_required = "curation.can_inventory"
    template_name = "books/bookentry_cover_fetch.html"

    def get(self, request, pk: int):
        """Fetch from provider and show preview, or an error page if not found."""
        from books.cover_fetcher import fetch_cover

        book_entry = get_object_or_404(BookEntry, pk=pk)

        isbn = book_entry.isbn or ""
        ean = book_entry.ean or ""

        if not isbn and not (ean and (ean.startswith("978") or ean.startswith("979"))):
            return render(
                request,
                self.template_name,
                {
                    "book_entry": book_entry,
                    "error": "no_isbn",
                },
            )

        result = fetch_cover(isbn=isbn, ean=ean)

        if not result:
            return render(
                request,
                self.template_name,
                {
                    "book_entry": book_entry,
                    "error": "not_found",
                    "isbn": isbn,
                    "ean": ean,
                },
            )

        image_b64 = base64.b64encode(result.image_bytes).decode()
        return render(
            request,
            self.template_name,
            {
                "book_entry": book_entry,
                "source": result.source,
                "isbn": isbn,
                "ean": ean,
                "content_type": result.content_type,
                "image_data_url": f"data:{result.content_type};base64,{image_b64}",
                "image_b64": image_b64,
            },
        )

    def post(self, request, pk: int):
        """Save the confirmed cover image."""
        book_entry = get_object_or_404(BookEntry, pk=pk)

        image_b64 = request.POST.get("image_b64", "")
        content_type = request.POST.get("content_type", "image/jpeg")
        source = request.POST.get("source", "")
        isbn = book_entry.isbn or ""
        ean = book_entry.ean or ""
        identifier = isbn or ean
        id_label = "ISBN" if isbn else "EAN"

        if not image_b64:
            return redirect(book_entry.get_absolute_url())

        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception:
            return redirect(book_entry.get_absolute_url())

        ext = mimetypes.guess_extension(content_type) or ".jpg"
        if ext in (".jpe", ".jfif"):
            ext = ".jpg"
        filename = f"cover_{identifier}{ext}"

        BookEntryImage.objects.create(
            book_entry=book_entry,
            image=ContentFile(image_bytes, name=filename),
            image_type=BookEntryImage.ImageType.COVER,
            caption=f"Fetched from {source} ({id_label}: {identifier})",
            order=0,
        )
        return redirect(book_entry.get_absolute_url())


@dataclass
class _DownsampledFrame:
    """A downsampled working copy of the source image, and how to scale back up."""

    small: "np.ndarray"
    sh: int
    sw: int
    scale: float
    w: int
    h: int


def _scale_box(box, pad: int, frame: _DownsampledFrame) -> dict:
    """Scale a (bx, by, bw, bh) box detected in the downsampled frame back to the original size."""
    bx, by, bw, bh = box
    inv = 1.0 / frame.scale
    x = max(0, int((bx - pad) * inv))
    y = max(0, int((by - pad) * inv))
    x2 = min(frame.w, int((bx + bw + pad) * inv))
    y2 = min(frame.h, int((by + bh + pad) * inv))
    return {"x": x, "y": y, "width": x2 - x, "height": y2 - y}


def _detect_by_background_subtraction(frame: _DownsampledFrame) -> dict | None:
    """Strategy 1: find the largest region differing from the estimated background colour.

    Samples the four corners (+ edge midpoints) to estimate the background
    (table / surface) colour. The book should be the largest region that
    differs from that colour.
    """
    small, sh, sw = frame.small, frame.sh, frame.sw
    corner_pixels = np.array(
        [
            small[0, 0],
            small[0, -1],
            small[-1, 0],
            small[-1, -1],
            small[0, sw // 2],
            small[-1, sw // 2],
            small[sh // 2, 0],
            small[sh // 2, -1],
        ],
        dtype=np.float32,
    )
    bg_color = np.median(corner_pixels, axis=0)
    # cv2.absdiff's scalar operand must be a 4-element float64 array (OpenCV's
    # internal Scalar type), not a 3-element BGR array or a plain tuple.
    bg_scalar = np.array([*bg_color, 0.0], dtype=np.float64)
    diff_gray = cv2.cvtColor(cv2.absdiff(small, bg_scalar), cv2.COLOR_BGR2GRAY)
    # Threshold: pixels more than 30 units away from background are foreground
    _, fg_mask = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)
    kernel5 = np.ones((5, 5), np.uint8)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel5, iterations=4)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel5, iterations=2)
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) <= sh * sw * 0.04:
        return None
    box = cv2.boundingRect(largest)
    _, _, bw, bh = box
    # Reject if it's the whole frame (detection failed)
    if bw >= sw * 0.98 and bh >= sh * 0.98:
        return None
    return _scale_box(box, 8, frame)


def _detect_by_edge_contours(frame: _DownsampledFrame) -> dict | None:
    """Strategy 2: find a quadrilateral-ish contour via edge detection."""
    gray = cv2.cvtColor(frame.small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (21, 21), 0), 30, 120)
    kernel3 = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel3, iterations=4)
    edges = cv2.dilate(edges, kernel3, iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    min_area = frame.sh * frame.sw * 0.04
    for contour in contours[:20]:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            break
        peri = cv2.arcLength(contour, True)
        for eps in (0.01, 0.02, 0.04, 0.06, 0.10):
            approx = cv2.approxPolyDP(contour, eps * peri, True)
            if not 4 <= len(approx) <= 6:
                continue
            box = cv2.boundingRect(approx)
            box_area = float(box[2] * box[3])
            if box_area < min_area:
                continue
            if area / box_area > 0.45:
                return _scale_box(box, 5, frame)
            break
    return None


def _fallback_crop(w, h) -> dict:
    """Fallback: centred portrait (2:3) crop when neither detection strategy fires."""
    tw = int(h * 2 / 3)
    if tw <= w:
        return {"x": (w - tw) // 2, "y": 0, "width": tw, "height": h}
    th = int(w * 3 / 2)
    if th <= h:
        return {"x": 0, "y": (h - th) // 2, "width": w, "height": th}
    return {"x": 0, "y": 0, "width": w, "height": h}


def _detect_book_cover(img: "np.ndarray") -> dict:
    """Return crop box {x, y, width, height} for the most prominent rectangle in img."""
    h, w = img.shape[:2]

    # --- Downsample to ≤800 px on the long edge ---
    max_dim = 800
    scale = min(max_dim / max(h, w), 1.0)
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    frame = _DownsampledFrame(small=small, sh=sh, sw=sw, scale=scale, w=w, h=h)

    box = _detect_by_background_subtraction(frame)
    if box is not None:
        return box

    box = _detect_by_edge_contours(frame)
    if box is not None:
        return box

    return _fallback_crop(w, h)


class BookEntryCoverDetectView(PermissionRequiredMixin, View):
    """Detect book cover rectangle in an uploaded image and return crop coordinates."""

    permission_required = "curation.can_inventory"

    def post(self, request):
        """Accept an image, run contour detection, return JSON crop box."""
        image_file = request.FILES.get("image")
        if not image_file:
            return JsonResponse({"error": "no image"}, status=400)
        data = image_file.read()
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return JsonResponse({"error": "invalid image"}, status=400)
        return JsonResponse(_detect_book_cover(img))


def _to_jpeg_bytes(image_file) -> bytes:
    """Convert any image (including HEIC) to JPEG bytes using Pillow."""
    pillow_heif.register_heif_opener()

    image_file.seek(0)
    img: Image.Image = Image.open(image_file)
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


class BookEntryImageConvertView(PermissionRequiredMixin, View):
    """Convert an uploaded image to JPEG and return it — used client-side for HEIC preview."""

    permission_required = "curation.can_inventory"

    def post(self, request):
        """Accept any image file, return it as a JPEG."""

        image_file = request.FILES.get("image")
        if not image_file:
            return JsonResponse({"error": "no image"}, status=400)
        try:
            jpeg_bytes = _to_jpeg_bytes(image_file)
        except Exception:
            return JsonResponse({"error": "conversion failed"}, status=400)
        return HttpResponse(jpeg_bytes, content_type="image/jpeg")
