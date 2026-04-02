"""PDF ingestion service: supported-PDF gate (B2) and section detection (B1).

B2 — check_pdf_supported():
    Rejects image-only, encrypted, and corrupt PDFs before any DB writes.

B1 — ingest_resume():
    Parses a resume PDF into deterministically ordered ResumeSection objects,
    each with a bounding box in PDF bottom-left user-space coordinates.

Contract reference: docs/contracts/section-output-schema.md v1.0.0
"""

import re
from collections import Counter
from typing import NamedTuple

import fitz  # PyMuPDF

from resume_sessions.models import ResumeSection, ResumeSession

from .exceptions import UnsupportedPDFError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Canonical mapping: normalised heading text → section_key
_SECTION_KEY_MAP: dict[str, str] = {
    "contact": "contact",
    "contact information": "contact",
    "contact info": "contact",
    "personal information": "contact",
    "personal details": "contact",
    "summary": "summary",
    "professional summary": "summary",
    "career summary": "summary",
    "executive summary": "summary",
    "profile": "summary",
    "about me": "summary",
    "objective": "objective",
    "career objective": "objective",
    "professional objective": "objective",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "employment history": "experience",
    "work history": "experience",
    "career history": "experience",
    "education": "education",
    "academic background": "education",
    "educational background": "education",
    "academic history": "education",
    "skills": "skills",
    "technical skills": "skills",
    "core competencies": "skills",
    "competencies": "skills",
    "key skills": "skills",
    "professional skills": "skills",
    "projects": "projects",
    "personal projects": "projects",
    "academic projects": "projects",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "awards": "awards",
    "achievements": "awards",
    "honors": "awards",
    "honours": "awards",
    "publications": "publications",
    "languages": "languages",
    "interests": "interests",
    "hobbies": "interests",
    "activities": "interests",
    "references": "references",
    "volunteer": "volunteer",
    "volunteering": "volunteer",
    "volunteer experience": "volunteer",
    "community service": "volunteer",
}

# PyMuPDF span flags bitmask bit for bold
_BOLD_FLAG = 1 << 4  # 16

# Minimum extractable characters required to pass the B2 gate.
# Set conservatively low so very short resumes don't get rejected;
# the real rejection target is image-only PDFs which produce zero text.
_MIN_TEXT_CHARS = 20


# ---------------------------------------------------------------------------
# Internal data structure
# ---------------------------------------------------------------------------


class _Block(NamedTuple):
    """Normalised representation of one PyMuPDF text block."""

    page_no: int         # zero-based page index
    page_height: float   # page height in points
    fitz_x0: float
    fitz_y0: float
    fitz_x1: float
    fitz_y1: float
    text: str            # stripped concatenated text of the block
    is_heading: bool
    font_size: float
    is_bold: bool


# ---------------------------------------------------------------------------
# B2: Supported-PDF gate
# ---------------------------------------------------------------------------


def check_pdf_supported(pdf_path: str) -> None:
    """Raise UnsupportedPDFError if the PDF cannot be parsed into text.

    Checks performed in order:
    1. Document opens without error (not corrupted / unrecognised format).
    2. Not encrypted / password-protected.
    3. Contains at least ``_MIN_TEXT_CHARS`` extractable characters
       (rejects image-only PDFs where all content is raster images).
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise UnsupportedPDFError(f"Cannot open PDF: {exc}") from exc

    with doc:
        if doc.is_encrypted:
            raise UnsupportedPDFError(
                "PDF is encrypted or password-protected and cannot be parsed."
            )

        total_text = "".join(page.get_text("text") for page in doc)
        if len(total_text.strip()) < _MIN_TEXT_CHARS:
            raise UnsupportedPDFError(
                "PDF contains insufficient extractable text. "
                "It may be image-only or blank."
            )


# ---------------------------------------------------------------------------
# B1: Section detection and ingestion
# ---------------------------------------------------------------------------


def ingest_resume(
    session: ResumeSession,
    pdf_path: str,
) -> list[ResumeSection]:
    """Parse *pdf_path* into ResumeSection objects and persist them.

    Calls check_pdf_supported first so no DB writes occur for unsupported PDFs.
    Returns the saved sections ordered by order_index (zero-based, contiguous).

    Contract invariants enforced:
    - order_index values form a contiguous zero-based sequence.
    - section_key values are unique within the session.
    - bounding_box satisfies x0 < x1 and y0 < y1.
    - original_content is never empty.
    """
    check_pdf_supported(pdf_path)

    with fitz.open(pdf_path) as doc:
        blocks = _extract_blocks(doc)

    section_data = _build_sections(blocks)

    saved: list[ResumeSection] = []
    for order_index, sd in enumerate(section_data):
        section = ResumeSection(
            session=session,
            section_key=sd["section_key"],
            order_index=order_index,
            page_number=sd["page_number"],
            bbox_x0=sd["bbox_x0"],
            bbox_y0=sd["bbox_y0"],
            bbox_x1=sd["bbox_x1"],
            bbox_y1=sd["bbox_y1"],
            original_content=sd["original_content"],
        )
        section.save()
        saved.append(section)

    return saved


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_blocks(doc: fitz.Document) -> list[_Block]:
    """Extract and classify all text blocks from *doc*."""
    raw: list[_Block] = []

    for page in doc:
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        page_height = page.rect.height

        for block in page_dict["blocks"]:
            if block["type"] != 0:  # skip image blocks
                continue

            block_text = ""
            max_size = 0.0
            block_bold = False

            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"]
                    if span["size"] > max_size:
                        max_size = span["size"]
                    if span["flags"] & _BOLD_FLAG:
                        block_bold = True

            stripped = block_text.strip()
            if not stripped:
                continue

            raw.append(
                _Block(
                    page_no=page.number,
                    page_height=page_height,
                    fitz_x0=block["bbox"][0],
                    fitz_y0=block["bbox"][1],
                    fitz_x1=block["bbox"][2],
                    fitz_y1=block["bbox"][3],
                    text=stripped,
                    is_heading=False,  # determined below
                    font_size=max_size,
                    is_bold=block_bold,
                )
            )

    if not raw:
        return []

    # Determine body font size as the most common size across all blocks
    body_size = Counter(b.font_size for b in raw).most_common(1)[0][0]

    return [b._replace(is_heading=_classify_heading(b, body_size)) for b in raw]


def _classify_heading(block: _Block, body_size: float) -> bool:
    """Return True if *block* looks like a resume section heading."""
    text = block.text

    # Paragraphs of content are never headings
    if len(text) > 80:
        return False
    if text.count("\n") > 2:
        return False

    normalized = _normalize_heading(text)

    # Known resume section keyword → always a heading
    if normalized in _SECTION_KEY_MAP:
        return True

    # All-uppercase short text (e.g. "EXPERIENCE", "SKILLS")
    cleaned_alpha = re.sub(r"[^A-Za-z]", "", text)
    if cleaned_alpha and cleaned_alpha == cleaned_alpha.upper() and len(cleaned_alpha) > 2:
        return True

    # Larger than body text by at least 1.5 pts
    if block.font_size >= body_size + 1.5:
        return True

    # Bold and brief (≤ 6 words)
    if block.is_bold and len(text.split()) <= 6:
        return True

    return False


def _normalize_heading(text: str) -> str:
    """Lowercase and normalise *text* for section-key lookup."""
    lowered = text.lower().strip()
    # Strip trailing punctuation (colons, dashes, underscores)
    lowered = re.sub(r"[:\-_]+$", "", lowered).strip()
    # Collapse whitespace
    return re.sub(r"\s+", " ", lowered)


def _section_key_for(heading_text: str, used_keys: set[str]) -> str:
    """Derive a unique section_key from *heading_text*, recording it in *used_keys*."""
    normalized = _normalize_heading(heading_text)
    base_key = _SECTION_KEY_MAP.get(normalized)
    if base_key is None:
        # Derive from heading text: replace non-alphanumeric runs with _
        # `normalized` is already lowercased, but use A-Z range for resilience
        base_key = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_") or "section"

    key = base_key
    counter = 2
    while key in used_keys:
        key = f"{base_key}_{counter}"
        counter += 1

    used_keys.add(key)
    return key


def _to_bottom_left(
    fitz_x0: float,
    fitz_y0: float,
    fitz_x1: float,
    fitz_y1: float,
    page_height: float,
) -> tuple[float, float, float, float]:
    """Convert PyMuPDF top-left coordinates to PDF bottom-left user-space.

    PyMuPDF: origin top-left, y increases downward.
    Contract: origin bottom-left, y increases upward.
    """
    return (
        fitz_x0,
        page_height - fitz_y1,  # bottom in contract coords
        fitz_x1,
        page_height - fitz_y0,  # top in contract coords
    )


def _build_sections(blocks: list[_Block]) -> list[dict]:
    """Group *blocks* into section dicts using detected headings.

    Content that appears before the first heading is treated as a ``contact``
    section (name, address, phone — typical resume header content).
    """
    if not blocks:
        return []

    used_keys: set[str] = set()
    sections: list[dict] = []

    current_heading: _Block | None = None
    current_content: list[_Block] = []

    for blk in blocks:
        if blk.is_heading:
            _flush_section(current_heading, current_content, sections, used_keys)
            current_heading = blk
            current_content = []
        else:
            current_content.append(blk)

    _flush_section(current_heading, current_content, sections, used_keys)

    return sections


def _flush_section(
    heading: _Block | None,
    content: list[_Block],
    sections: list[dict],
    used_keys: set[str],
) -> None:
    """Append one section dict to *sections* from *heading* + *content* blocks."""
    all_blocks = ([heading] if heading is not None else []) + content

    original_content = "\n\n".join(b.text for b in all_blocks if b.text).strip()
    if not original_content:
        return

    # Section key
    if heading is not None:
        section_key = _section_key_for(heading.text, used_keys)
    else:
        # Pre-heading content: contact / header block
        section_key = _section_key_for("contact", used_keys)

    # page_number is one-based; sourced from the first block of the section
    first_block = all_blocks[0]
    page_number = first_block.page_no + 1
    page_height = first_block.page_height

    # Bounding box: union of all blocks on the section's start page
    # (multi-page content keeps bbox on the start page only)
    start_page_blocks = [b for b in all_blocks if b.page_no == first_block.page_no]
    fitz_x0 = min(b.fitz_x0 for b in start_page_blocks)
    fitz_y0 = min(b.fitz_y0 for b in start_page_blocks)
    fitz_x1 = max(b.fitz_x1 for b in start_page_blocks)
    fitz_y1 = max(b.fitz_y1 for b in start_page_blocks)

    bbox_x0, bbox_y0, bbox_x1, bbox_y1 = _to_bottom_left(
        fitz_x0, fitz_y0, fitz_x1, fitz_y1, page_height
    )

    sections.append(
        {
            "section_key": section_key,
            "page_number": page_number,
            "bbox_x0": bbox_x0,
            "bbox_y0": bbox_y0,
            "bbox_x1": bbox_x1,
            "bbox_y1": bbox_y1,
            "original_content": original_content,
        }
    )
