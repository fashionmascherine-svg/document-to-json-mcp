"""
PDF text extraction module.
Supports native PDF text extraction (PyMuPDF) and OCR (Tesseract) for scanned documents.
"""
import io
from typing import Optional, Tuple
import httpx
import fitz  # PyMuPDF
from PIL import Image
from src.config import MAX_FILE_SIZE_MB, MAX_PAGES, DEFAULT_LANGUAGE


class PDFExtractionError(Exception):
    """Base exception for PDF extraction failures."""
    pass


class FileTooLargeError(PDFExtractionError):
    """Raised when PDF exceeds size limit."""
    pass


class PDFExtractor:
    """Extracts text content from PDF files, with fallback to OCR for scanned docs."""

    def __init__(self, max_file_size_mb: int = MAX_FILE_SIZE_MB, max_pages: int = MAX_PAGES):
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_pages = max_pages

    async def download_pdf(self, url: str) -> bytes:
        """
        Download a PDF from a public URL.
        
        Args:
            url: Public URL to the PDF file.
        
        Returns:
            Raw PDF bytes.
        
        Raises:
            FileTooLargeError: If PDF exceeds size limit.
            PDFExtractionError: If download fails.
        """
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.content

                if len(content) > self.max_file_size_bytes:
                    raise FileTooLargeError(
                        f"File too large: {len(content)} bytes "
                        f"(max {self.max_file_size_bytes})"
                    )

                return content

        except httpx.TimeoutException:
            raise PDFExtractionError("PDF download timed out (max 30s)")
        except httpx.HTTPStatusError as e:
            raise PDFExtractionError(f"Failed to download PDF: HTTP {e.response.status_code}")
        except Exception as e:
            raise PDFExtractionError(f"Download failed: {str(e)}")

    def extract_text(self, pdf_bytes: bytes) -> Tuple[str, bool]:
        """
        Extract text from PDF bytes.
        
        First attempts native text extraction via PyMuPDF.
        If pages have < 50 chars, falls back to OCR.
        
        Args:
            pdf_bytes: Raw PDF file bytes.
        
        Returns:
            Tuple of (extracted_text, used_ocr_flag).
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise PDFExtractionError(f"Invalid PDF file: {str(e)}")

        page_count = min(len(doc), self.max_pages)
        if page_count == 0:
            raise PDFExtractionError("PDF has no pages")

        # Try native text extraction first
        text_parts = []
        needs_ocr = False

        for page_num in range(page_count):
            page = doc[page_num]
            page_text = page.get_text().strip()

            if len(page_text) < 50:
                # Page likely contains only images (scanned document)
                needs_ocr = True
                break
            text_parts.append(page_text)

        doc.close()

        if needs_ocr:
            return self._ocr_pdf(pdf_bytes, page_count), True

        return "\n\n--- PAGE BREAK ---\n\n".join(text_parts), False

    def _ocr_pdf(self, pdf_bytes: bytes, max_pages: int) -> str:
        """
        Convert PDF pages to images and run OCR via Tesseract.
        If Poppler/pdf2image is not installed, returns native text as fallback.
        
        Args:
            pdf_bytes: Raw PDF file bytes.
            max_pages: Maximum number of pages to OCR.
        
        Returns:
            OCR-extracted text or native text fallback.
        """
        try:
            from pdf2image import convert_from_bytes
        except ImportError:
            # pdf2image not installed, return native text instead
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            for page_num in range(min(len(doc), max_pages)):
                text_parts.append(doc[page_num].get_text().strip())
            doc.close()
            text = "\n\n--- PAGE BREAK ---\n\n".join(text_parts)
            if not text.strip():
                text = "[OCR not available - pdf2image not installed. Install with: pip install pdf2image]"
            return text

        # Check if poppler is available
        try:
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=max_pages)
        except Exception as e:
            # Poppler not available, fall back to native text
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            for page_num in range(min(len(doc), max_pages)):
                text_parts.append(doc[page_num].get_text().strip())
            doc.close()
            text = "\n\n--- PAGE BREAK ---\n\n".join(text_parts)
            if not text.strip():
                text = f"[OCR not available - Poppler not installed. Install poppler-utils. Error: {e}]"
            return text

        import pytesseract
        text_parts = []
        for i, img in enumerate(images):
            try:
                text = pytesseract.image_to_string(img, lang=DEFAULT_LANGUAGE.replace("+", "+"))
                text_parts.append(f"--- PAGE {i+1} ---\n{text}")
            except Exception as e:
                text_parts.append(f"--- PAGE {i+1} ---\n[OCR Error: {str(e)}]")

        return "\n\n".join(text_parts)

    def detect_is_scanned(self, pdf_bytes: bytes) -> bool:
        """
        Quick check if a PDF is a scanned document (image-based).
        
        Args:
            pdf_bytes: Raw PDF file bytes.
        
        Returns:
            True if the first page has little extractable text.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if len(doc) == 0:
                return False
            text = doc[0].get_text().strip()
            doc.close()
            return len(text) < 50
        except Exception:
            return False
