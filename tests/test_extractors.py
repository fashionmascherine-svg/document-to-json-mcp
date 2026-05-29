"""
Tests for PDF extraction module.
Requires sample PDF files in tests/sample_invoices/.
"""
import pytest
from src.extractors.pdf import PDFExtractor, FileTooLargeError, PDFExtractionError


@pytest.fixture
def extractor():
    return PDFExtractor(max_file_size_mb=5, max_pages=10)


class TestPDFDownload:
    """Tests for PDF download functionality."""

    async def test_download_invalid_url(self, extractor):
        """Should raise error on invalid URL."""
        with pytest.raises(PDFExtractionError):
            await extractor.download_pdf("https://invalid.url/nonexistent.pdf")

    async def test_download_empty_url(self, extractor):
        """Should raise error on empty URL."""
        with pytest.raises(PDFExtractionError):
            await extractor.download_pdf("")


class TestPDFTextExtraction:
    """Tests for PDF text extraction (requires sample files)."""

    def test_detect_scanned_empty(self, extractor):
        """Empty bytes should return False for scanned detection."""
        assert extractor.detect_is_scanned(b"") is False

    def test_extract_text_empty(self, extractor):
        """Empty bytes should raise error."""
        with pytest.raises(PDFExtractionError):
            extractor.extract_text(b"")


class TestValidation:
    """Tests for validation module."""

    def test_validate_invoice_missing_number(self):
        from src.validation import validate_invoice
        data = {"metadata": {}, "totals": {}, "line_items": []}
        warnings = validate_invoice(data)
        assert "Missing invoice_number" in warnings

    def test_validate_invoice_valid(self):
        from src.validation import validate_invoice
        data = {
            "metadata": {"invoice_number": "INV-001", "invoice_date": "2024-03-15"},
            "totals": {"net_total": 1000.0, "grand_total": 1220.0},
            "line_items": [
                {"net_amount": 1000.0, "total": 1220.0}
            ],
        }
        warnings = validate_invoice(data)
        assert len(warnings) == 0

    def test_validate_bank_statement_balance_mismatch(self):
        from src.validation import validate_bank_statement
        data = {
            "balances": {
                "opening_balance": 1000.0,
                "closing_balance": 500.0,
                "total_credits": 200.0,
                "total_debits": 100.0,
            },
            "transactions": [],
        }
        warnings = validate_bank_statement(data)
        # Expected closing: 1000 + 200 - 100 = 1100, but declared 500
        assert len(warnings) > 0

    def test_is_valid_iso_date(self):
        from src.validation import _is_valid_iso_date
        assert _is_valid_iso_date("2024-03-15") is True
        assert _is_valid_iso_date("15/03/2024") is False
        assert _is_valid_iso_date("not-a-date") is False
        assert _is_valid_iso_date("") is False
