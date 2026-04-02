"""Unit tests for document_ingestion services (B1 + B2).

Tests use real PyMuPDF to create in-memory PDFs; DB interactions are mocked.
"""

import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import fitz
import pytest

from document_ingestion.exceptions import UnsupportedPDFError
from document_ingestion.services import (
    _build_sections,
    _classify_heading,
    _normalize_heading,
    _section_key_for,
    _to_bottom_left,
    check_pdf_supported,
    ingest_resume,
)


# ---------------------------------------------------------------------------
# PDF fixture helpers
# ---------------------------------------------------------------------------


def _write_pdf(doc: fitz.Document) -> str:
    """Save *doc* to a NamedTemporaryFile and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(tmp.name)
    tmp.close()
    return tmp.name


def _make_text_pdf(sections: list[tuple[str, str]]) -> str:
    """Create a single-page PDF with alternating heading / body text.

    *sections* is a list of (heading, body) tuples.  Headings are inserted
    at 14 pt; body text at 11 pt.  Returns the temp-file path.
    """
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        y = 80.0
        for heading, body in sections:
            page.insert_text((72, y), heading, fontsize=14)
            y += 24
            for line in body.splitlines():
                page.insert_text((72, y), line, fontsize=11)
                y += 16
            y += 12
        return _write_pdf(doc)


def _make_blank_pdf() -> str:
    """Create a PDF with no text at all (simulates image-only)."""
    with fitz.open() as doc:
        doc.new_page()
        return _write_pdf(doc)


def _make_encrypted_pdf() -> str:
    """Create a PDF encrypted with a user password."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "This content is protected.", fontsize=11)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(
        tmp.name,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="secret",
        owner_pw="owner",
    )
    tmp.close()
    doc.close()
    return tmp.name


# ---------------------------------------------------------------------------
# B2: check_pdf_supported
# ---------------------------------------------------------------------------


class TestCheckPdfSupported:
    def test_passes_for_text_pdf(self, tmp_path):
        path = _make_text_pdf([("EXPERIENCE", "Worked at Acme Corp for 3 years.")])
        check_pdf_supported(path)  # must not raise

    def test_raises_for_image_only_pdf(self):
        path = _make_blank_pdf()
        with pytest.raises(UnsupportedPDFError, match="insufficient extractable text"):
            check_pdf_supported(path)

    def test_raises_for_encrypted_pdf(self):
        path = _make_encrypted_pdf()
        with pytest.raises(UnsupportedPDFError, match="encrypted"):
            check_pdf_supported(path)

    def test_raises_for_nonexistent_file(self, tmp_path):
        with pytest.raises(UnsupportedPDFError, match="Cannot open PDF"):
            check_pdf_supported(str(tmp_path / "missing.pdf"))

    def test_raises_for_corrupt_file(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf at all")
        with pytest.raises(UnsupportedPDFError, match="Cannot open PDF"):
            check_pdf_supported(str(bad))


# ---------------------------------------------------------------------------
# B1: _normalize_heading
# ---------------------------------------------------------------------------


class TestNormalizeHeading:
    def test_lowercases(self):
        assert _normalize_heading("EXPERIENCE") == "experience"

    def test_strips_trailing_colon(self):
        assert _normalize_heading("Skills:") == "skills"

    def test_strips_trailing_dash(self):
        assert _normalize_heading("Education -") == "education"

    def test_collapses_whitespace(self):
        assert _normalize_heading("Work  Experience") == "work experience"

    def test_strips_leading_trailing_spaces(self):
        assert _normalize_heading("  Summary  ") == "summary"


# ---------------------------------------------------------------------------
# B1: _section_key_for
# ---------------------------------------------------------------------------


class TestSectionKeyFor:
    def test_known_key_maps_to_canonical(self):
        used: set[str] = set()
        assert _section_key_for("EXPERIENCE", used) == "experience"

    def test_known_key_variant(self):
        used: set[str] = set()
        assert _section_key_for("Work Experience", used) == "experience"

    def test_unknown_key_derived_from_text(self):
        used: set[str] = set()
        key = _section_key_for("Awards & Honors", used)
        assert key  # non-empty
        assert " " not in key

    def test_duplicate_key_gets_suffix(self):
        used: set[str] = set()
        k1 = _section_key_for("EXPERIENCE", used)
        k2 = _section_key_for("Work Experience", used)
        assert k1 != k2
        assert k2 == "experience_2"

    def test_used_keys_updated(self):
        used: set[str] = set()
        _section_key_for("SKILLS", used)
        assert "skills" in used


# ---------------------------------------------------------------------------
# B1: _to_bottom_left
# ---------------------------------------------------------------------------


class TestToBottomLeft:
    def test_conversion_letter_page(self):
        # PyMuPDF coords: top-left origin, y0=100, y1=200 on a 792pt page
        x0, y0, x1, y1 = _to_bottom_left(72, 100, 540, 200, 792)
        assert x0 == 72
        assert x1 == 540
        assert y0 == pytest.approx(592)  # 792 - 200
        assert y1 == pytest.approx(692)  # 792 - 100

    def test_y0_less_than_y1(self):
        x0, y0, x1, y1 = _to_bottom_left(10, 50, 200, 150, 500)
        assert y0 < y1

    def test_x_coords_unchanged(self):
        x0, y0, x1, y1 = _to_bottom_left(30, 40, 300, 400, 800)
        assert x0 == 30
        assert x1 == 300


# ---------------------------------------------------------------------------
# B1: _classify_heading
# ---------------------------------------------------------------------------


class TestClassifyHeading:
    def _block(self, text, font_size=11.0, is_bold=False):
        from document_ingestion.services import _Block

        return _Block(
            page_no=0,
            page_height=792,
            fitz_x0=72,
            fitz_y0=100,
            fitz_x1=300,
            fitz_y1=115,
            text=text,
            is_heading=False,
            font_size=font_size,
            is_bold=is_bold,
        )

    def test_all_caps_short_is_heading(self):
        assert _classify_heading(self._block("EXPERIENCE"), 11.0) is True

    def test_known_keyword_is_heading(self):
        assert _classify_heading(self._block("Education"), 11.0) is True

    def test_larger_font_is_heading(self):
        assert _classify_heading(self._block("Some Section", font_size=14.0), 11.0) is True

    def test_bold_short_is_heading(self):
        assert _classify_heading(self._block("Work History", is_bold=True), 11.0) is True

    def test_long_text_not_heading(self):
        long_text = "This is a very long paragraph that definitely is not a section header at all."
        assert _classify_heading(self._block(long_text), 11.0) is False

    def test_multiline_body_not_heading(self):
        multiline = "Line one\nLine two\nLine three\nLine four"
        assert _classify_heading(self._block(multiline), 11.0) is False

    def test_regular_body_text_not_heading(self):
        # short, not bold, same size, not all-caps, not a keyword
        assert _classify_heading(self._block("John Smith"), 11.0) is False


# ---------------------------------------------------------------------------
# B1: _build_sections
# ---------------------------------------------------------------------------


class TestBuildSections:
    def _make_blocks(self, specs):
        """Create _Block namedtuples from (text, is_heading) specs."""
        from document_ingestion.services import _Block

        blocks = []
        y = 80.0
        for text, is_heading in specs:
            blocks.append(
                _Block(
                    page_no=0,
                    page_height=792,
                    fitz_x0=72,
                    fitz_y0=y,
                    fitz_x1=540,
                    fitz_y1=y + 14,
                    text=text,
                    is_heading=is_heading,
                    font_size=14.0 if is_heading else 11.0,
                    is_bold=False,
                )
            )
            y += 20
        return blocks

    def test_empty_blocks_returns_empty(self):
        assert _build_sections([]) == []

    def test_single_heading_with_content(self):
        blocks = self._make_blocks([
            ("EXPERIENCE", True),
            ("Software Engineer at Acme Corp", False),
        ])
        sections = _build_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["section_key"] == "experience"
        assert "Software Engineer at Acme Corp" in sections[0]["original_content"]

    def test_pre_heading_content_is_contact(self):
        blocks = self._make_blocks([
            ("Jane Doe", False),
            ("jane@example.com", False),
            ("EXPERIENCE", True),
            ("Engineer", False),
        ])
        sections = _build_sections(blocks)
        assert sections[0]["section_key"] == "contact"
        assert sections[1]["section_key"] == "experience"

    def test_multiple_sections(self):
        blocks = self._make_blocks([
            ("EXPERIENCE", True),
            ("Built systems.", False),
            ("EDUCATION", True),
            ("B.S. CS, MIT", False),
            ("SKILLS", True),
            ("Python, Django", False),
        ])
        sections = _build_sections(blocks)
        assert len(sections) == 3
        keys = [s["section_key"] for s in sections]
        assert keys == ["experience", "education", "skills"]

    def test_order_index_via_enumerate(self):
        blocks = self._make_blocks([
            ("EXPERIENCE", True),
            ("content", False),
            ("EDUCATION", True),
            ("content", False),
        ])
        sections = _build_sections(blocks)
        # order_index is assigned by the caller (ingest_resume) via enumerate
        # _build_sections itself returns a list; verify position ordering
        assert sections[0]["section_key"] == "experience"
        assert sections[1]["section_key"] == "education"

    def test_section_keys_unique(self):
        blocks = self._make_blocks([
            ("EXPERIENCE", True),
            ("job 1", False),
            ("Work Experience", True),
            ("job 2", False),
        ])
        sections = _build_sections(blocks)
        keys = [s["section_key"] for s in sections]
        assert len(keys) == len(set(keys))

    def test_bounding_box_bottom_left_y0_lt_y1(self):
        blocks = self._make_blocks([
            ("EXPERIENCE", True),
            ("content here", False),
        ])
        sections = _build_sections(blocks)
        s = sections[0]
        assert s["bbox_y0"] < s["bbox_y1"]

    def test_page_number_one_based(self):
        blocks = self._make_blocks([("SKILLS", True), ("Python", False)])
        sections = _build_sections(blocks)
        assert sections[0]["page_number"] == 1  # page_no=0 → page_number=1

    def test_original_content_non_empty(self):
        blocks = self._make_blocks([("EDUCATION", True), ("MIT, 2020", False)])
        sections = _build_sections(blocks)
        assert sections[0]["original_content"].strip()


# ---------------------------------------------------------------------------
# Lightweight mock for ResumeSection (avoids Django FK validation)
# ---------------------------------------------------------------------------


@dataclass
class _MockSection:
    """Stand-in for ResumeSection that records constructor kwargs and fakes save."""

    session: object = None
    section_key: str = ""
    order_index: int = 0
    page_number: int = 1
    bbox_x0: float = 0.0
    bbox_y0: float = 0.0
    bbox_x1: float = 1.0
    bbox_y1: float = 1.0
    original_content: str = ""
    save_calls: int = field(default=0, repr=False)

    def save(self):
        self.save_calls += 1


@contextmanager
def _noop_atomic():
    """Context manager that replaces transaction.atomic for unit tests."""
    yield


def _mock_session():
    """Return a minimal session mock for ingest_resume unit tests."""
    session = MagicMock()
    session.sections.all.return_value.delete.return_value = None
    return session


# ---------------------------------------------------------------------------
# B1: ingest_resume (integration — DB mocked)
# ---------------------------------------------------------------------------


class TestIngestResume:
    def setup_method(self):
        self._atomic_patcher = patch(
            "document_ingestion.services.transaction.atomic", _noop_atomic
        )
        self._atomic_patcher.start()

    def teardown_method(self):
        self._atomic_patcher.stop()

    def test_returns_sections_for_valid_pdf(self):
        path = _make_text_pdf([
            ("EXPERIENCE", "Software Engineer at Acme Corp for three years."),
            ("EDUCATION", "B.S. Computer Science, Massachusetts Institute of Technology."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        assert len(sections) >= 2

    def test_order_index_contiguous_zero_based(self):
        path = _make_text_pdf([
            ("EXPERIENCE", "Worked on distributed systems at a large tech company."),
            ("EDUCATION", "Studied computer science and mathematics at university."),
            ("SKILLS", "Python, Django, Redis, PostgreSQL, Docker, Kubernetes."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        indices = [s.order_index for s in sections]
        assert indices == list(range(len(sections)))

    def test_section_keys_unique(self):
        path = _make_text_pdf([
            ("EXPERIENCE", "Worked as a software engineer at multiple companies."),
            ("EDUCATION", "Obtained bachelor and master degrees in computer science."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        keys = [s.section_key for s in sections]
        assert len(keys) == len(set(keys))

    def test_original_content_non_empty(self):
        path = _make_text_pdf([
            ("SKILLS", "Python, Django, Redis, PostgreSQL, Celery, Docker."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        for s in sections:
            assert s.original_content.strip()

    def test_bounding_box_valid(self):
        path = _make_text_pdf([
            ("EXPERIENCE", "Some work experience content at a well-known company."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        for s in sections:
            assert s.bbox_x0 < s.bbox_x1
            assert s.bbox_y0 < s.bbox_y1

    def test_page_number_one_based(self):
        path = _make_text_pdf([
            ("EDUCATION", "Received degree from MIT in 2020, graduated with honors."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        for s in sections:
            assert s.page_number >= 1

    def test_raises_unsupported_for_blank_pdf(self):
        path = _make_blank_pdf()
        with pytest.raises(UnsupportedPDFError):
            ingest_resume(_mock_session(), path)

    def test_raises_unsupported_for_encrypted_pdf(self):
        path = _make_encrypted_pdf()
        with pytest.raises(UnsupportedPDFError):
            ingest_resume(_mock_session(), path)

    def test_save_called_once_per_section(self):
        path = _make_text_pdf([
            ("EXPERIENCE", "Content one: led backend services team for two years."),
            ("EDUCATION", "Content two: studied engineering at a top university."),
        ])
        with patch("document_ingestion.services.ResumeSection", _MockSection):
            sections = ingest_resume(_mock_session(), path)
        for s in sections:
            assert s.save_calls == 1
