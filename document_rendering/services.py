"""Export service: converts approved session content into downloadable PDFs (D2).

Contract: docs/contracts/export-service-interface.md v1.0.0

Output rules (from the contract):
  - resume_only      → tailored-resume.pdf only
  - resume_and_cover_letter → tailored-resume.pdf + cover-letter.pdf as separate files
  - No ZIP output under any circumstance.

Coordinate system note:
  Section bounding boxes are stored in PDF user-space with a bottom-left origin
  (PDF spec, points).  PyMuPDF fitz.Rect uses a top-left origin (y increases
  downward).  The conversion is performed in _pdf_rect().
"""

import textwrap

import fitz  # PyMuPDF

from resume_sessions.models import CoverLetterDraft, ResumeSection, ResumeSession

# Typography constants used when inserting text into bounding boxes.
_RESUME_FONT_SIZE = 10
_COVER_LETTER_FONT_SIZE = 11
_COVER_LETTER_MARGIN_PT = 56  # ~0.78 inch margins (PDF points)
_COVER_LETTER_LINE_HEIGHT = 16


class ExportError(Exception):
    """Raised on unrecoverable export failures."""


def _pdf_rect(page: fitz.Page, bbox_x0: float, bbox_y0: float,
              bbox_x1: float, bbox_y1: float) -> fitz.Rect:
    """Convert a bottom-left-origin PDF bbox to a PyMuPDF top-left-origin Rect.

    PDF spec bbox: (x0, y0, x1, y1) where y0 < y1 and origin is bottom-left.
    fitz.Rect:     (x0, y0, x1, y1) where y0 < y1 and origin is top-left.
    """
    page_height = page.rect.height
    return fitz.Rect(
        bbox_x0,
        page_height - bbox_y1,  # top in fitz  = page_height - top-in-PDF
        bbox_x1,
        page_height - bbox_y0,  # bottom in fitz = page_height - bottom-in-PDF
    )


class ExportService:
    """Builds PDF byte streams for resume and cover letter artifacts.

    Contract: export-service-interface.md v1.0.0
    """

    def build_resume_pdf(
        self,
        session: ResumeSession,
        sections: list[ResumeSection],
        source_pdf_bytes: bytes | None = None,
    ) -> bytes:
        """Return PDF bytes for tailored-resume.pdf.

        If *source_pdf_bytes* is supplied the service overlays resolved text on
        top of each section's bounding box.  When no source bytes are available
        (e.g. storage not yet configured) a plain-text fallback PDF is produced.

        Args:
            session: The owning ResumeSession.
            sections: Ordered list of ResumeSections (resolved_content is used).
            source_pdf_bytes: Raw bytes of the original uploaded PDF, or None.

        Returns:
            PDF byte string for tailored-resume.pdf.

        Raises:
            ExportError: On unrecoverable fitz errors.
        """
        if source_pdf_bytes:
            return self._overlay_resume(source_pdf_bytes, sections)
        return self._plain_resume(session, sections)

    def build_cover_letter_pdf(self, draft: CoverLetterDraft) -> bytes:
        """Return PDF bytes for cover-letter.pdf.

        A new single-page (auto-expanding) PDF document is produced from the
        resolved cover letter content.

        Args:
            draft: The CoverLetterDraft whose resolved_content will be used.

        Returns:
            PDF byte string for cover-letter.pdf.

        Raises:
            ExportError: On unrecoverable fitz errors.
        """
        try:
            return self._build_cover_letter(draft.resolved_content)
        except Exception as exc:
            raise ExportError(f"Cover letter PDF build failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _overlay_resume(self, source_bytes: bytes, sections: list[ResumeSection]) -> bytes:
        """Overlay resolved section text onto the source PDF."""
        try:
            doc = fitz.open(stream=source_bytes, filetype="pdf")
        except Exception as exc:
            raise ExportError(f"Cannot open source PDF: {exc}") from exc

        try:
            for section in sections:
                page_idx = section.page_number - 1  # page_number is 1-based
                if page_idx < 0 or page_idx >= doc.page_count:
                    continue
                page = doc[page_idx]
                rect = _pdf_rect(
                    page,
                    section.bbox_x0,
                    section.bbox_y0,
                    section.bbox_x1,
                    section.bbox_y1,
                )
                # Redact the original text in the bounding box.
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
                # Insert resolved content.
                page.insert_textbox(
                    rect,
                    section.resolved_content,
                    fontsize=_RESUME_FONT_SIZE,
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
            return doc.tobytes(garbage=4, deflate=True)
        finally:
            doc.close()

    def _plain_resume(self, session: ResumeSession, sections: list[ResumeSection]) -> bytes:
        """Build a plain-text resume PDF when the source PDF is not available."""
        try:
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4
            margin = 56
            x0, x1 = margin, 595 - margin
            y = margin
            line_height = _RESUME_FONT_SIZE + 4

            for section in sections:
                heading = section.section_key.replace("_", " ").title()
                page.insert_text(
                    (x0, y),
                    heading,
                    fontsize=_RESUME_FONT_SIZE + 2,
                    color=(0.42, 0.35, 0.80),
                )
                y += line_height + 2
                content_rect = fitz.Rect(x0, y, x1, y + 200)
                rc = page.insert_textbox(
                    content_rect,
                    section.resolved_content,
                    fontsize=_RESUME_FONT_SIZE,
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                # rc is the unused vertical space (negative = overflow)
                used_height = 200 + min(0, rc)
                y += used_height + 12
                if y > 842 - margin:
                    page = doc.new_page(width=595, height=842)
                    y = margin

            return doc.tobytes(garbage=4, deflate=True)
        except Exception as exc:
            raise ExportError(f"Plain resume PDF build failed: {exc}") from exc
        finally:
            doc.close()

    def _build_cover_letter(self, content: str) -> bytes:
        """Build a simple cover-letter PDF from raw text."""
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4
        m = _COVER_LETTER_MARGIN_PT
        text_width = 595 - 2 * m
        # Wrap text to fit the text width (approx 80 chars for 11pt on A4).
        chars_per_line = int(text_width / (_COVER_LETTER_FONT_SIZE * 0.55))
        wrapped = textwrap.fill(content, width=max(40, chars_per_line))

        rect = fitz.Rect(m, m, 595 - m, 842 - m)
        rc = page.insert_textbox(
            rect,
            wrapped,
            fontsize=_COVER_LETTER_FONT_SIZE,
            color=(0, 0, 0),
            align=fitz.TEXT_ALIGN_LEFT,
        )
        # If content overflows one page, add continuation pages.
        if rc < 0:
            lines = wrapped.split("\n")
            line_h = _COVER_LETTER_LINE_HEIGHT
            lines_per_page = int((842 - 2 * m) / line_h)
            for chunk_start in range(lines_per_page, len(lines), lines_per_page):
                chunk = "\n".join(lines[chunk_start: chunk_start + lines_per_page])
                page = doc.new_page(width=595, height=842)
                page.insert_textbox(
                    fitz.Rect(m, m, 595 - m, 842 - m),
                    chunk,
                    fontsize=_COVER_LETTER_FONT_SIZE,
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )

        result = doc.tobytes(garbage=4, deflate=True)
        doc.close()
        return result
