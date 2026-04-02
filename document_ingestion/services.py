"""PDF validation service for document ingestion.

Contracts:
  - section-output-schema v1.0.0 (unsupported PDF detection)
  - generation-service-interface v1.0.0 (error_code: unsupported_pdf)

Image-only PDFs (scanned documents without a selectable text layer) are
rejected early so that failed generation attempts are prevented.
"""

import fitz  # PyMuPDF


def is_pdf_text_extractable(file_bytes: bytes) -> bool:
    """Return True if the PDF contains at least one page with extractable text.

    A PDF is considered unsupported when every page contains zero characters
    of selectable text — i.e. it was produced by scanning and has no text layer.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        True  — at least one page has selectable text.
        False — file is unreadable, not a valid PDF, or is entirely image-only.
    """
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                if page.get_text().strip():
                    return True
    except Exception:
        return False
    return False
