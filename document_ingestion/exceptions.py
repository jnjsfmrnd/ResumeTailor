"""Exceptions for the document_ingestion app."""


class UnsupportedPDFError(Exception):
    """Raised when a PDF cannot be parsed into extractable text sections.

    Triggers the B2 early-rejection path (image-only, encrypted, or
    corrupt PDFs).  Callers should map this to GenerationRun.ErrorCode.UNSUPPORTED_PDF.
    """
