"""Turn an uploaded document into page images.

Shared by every extraction backend: the vision-LLM path sends these images to a
model, and the offline OCR engine runs Tesseract over them. Images are used
as-is; PDFs are rasterized with ``pypdfium2`` (a pip wheel — no system poppler).
"""

from io import BytesIO

from fastapi import HTTPException, status

from .config import get_settings

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def rasterize_pdf(pdf_bytes: bytes) -> list[bytes]:
    """Render each PDF page to PNG bytes using pypdfium2 (no system poppler)."""
    import pypdfium2 as pdfium

    scale = get_settings().pdf_render_scale
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        pages: list[bytes] = []
        for page in pdf:
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            buf = BytesIO()
            image.save(buf, format="PNG")
            pages.append(buf.getvalue())
            bitmap.close()
            page.close()
        return pages
    finally:
        pdf.close()


def to_images(file_bytes: bytes, content_type: str) -> list[tuple[bytes, str]]:
    """Return a list of ``(image_bytes, media_type)`` for the uploaded document."""
    if content_type == "application/pdf":
        pages = rasterize_pdf(file_bytes)
        if not pages:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "PDF has no pages")
        return [(p, "image/png") for p in pages]
    if content_type in SUPPORTED_IMAGE_TYPES:
        return [(file_bytes, content_type)]
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported file type '{content_type}'. Allowed: PDF, PNG, JPEG, WEBP, GIF.",
    )
