"""
PDF Tools

Tools for reading and extracting content from PDF documents.
Optimized for insurance policy documents and certificates.
"""

from pathlib import Path

import fitz  # pymupdf
from agno.tools.toolkit import Toolkit

from app.observability import observe_tool


class PDFTools(Toolkit):
    """Tools for reading PDF documents."""

    def __init__(self):
        """Initialize PDF tools."""
        super().__init__(name="pdf")

        # Register tools explicitly
        self.register(self.read_pdf)
        self.register(self.read_pdf_page)
        self.register(self.get_pdf_info)

    @observe_tool
    def read_pdf(self, file_path: str, max_pages: int = 50) -> str:
        """
        Read and extract all text content from a PDF file.

        Args:
            file_path: Path to the PDF file (absolute or relative)
            max_pages: Maximum number of pages to extract (default 50)

        Returns:
            str: Extracted text content from the PDF
        """
        path = Path(file_path).expanduser().resolve()

        if not path.exists():
            return f"ERROR: File not found: {file_path}"

        if not path.suffix.lower() == ".pdf":
            return f"ERROR: Not a PDF file: {file_path}"

        try:
            doc = fitz.open(str(path))
            total_pages = len(doc)
            pages_to_read = min(total_pages, max_pages)
            text_content = []

            for page_num in range(pages_to_read):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_content.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()

            if not text_content:
                return f"PDF has {total_pages} pages but no extractable text (may be scanned/image-based)"

            result = "\n\n".join(text_content)

            if total_pages > max_pages:
                result += f"\n\n[INFO: Showing {max_pages} of {total_pages} total pages. Use read_pdf_page for specific pages.]"

            return result

        except Exception as e:
            return f"ERROR reading PDF: {str(e)}"

    @observe_tool
    def read_pdf_page(self, file_path: str, page_number: int) -> str:
        """
        Read a specific page from a PDF file.

        Args:
            file_path: Path to the PDF file
            page_number: Page number to read (1-indexed)

        Returns:
            str: Text content from the specified page
        """
        path = Path(file_path).expanduser().resolve()

        if not path.exists():
            return f"ERROR: File not found: {file_path}"

        try:
            doc = fitz.open(str(path))
            total_pages = len(doc)

            if page_number < 1 or page_number > total_pages:
                doc.close()
                return f"ERROR: Page {page_number} out of range. PDF has {total_pages} pages."

            page = doc[page_number - 1]  # Convert to 0-indexed
            text = page.get_text()
            doc.close()

            if not text.strip():
                return f"Page {page_number} has no extractable text (may be scanned/image-based)"

            return f"--- Page {page_number} of {total_pages} ---\n{text}"

        except Exception as e:
            return f"ERROR reading PDF page: {str(e)}"

    @observe_tool
    def get_pdf_info(self, file_path: str) -> str:
        """
        Get metadata and information about a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            str: PDF metadata including page count, title, author, etc.
        """
        path = Path(file_path).expanduser().resolve()

        if not path.exists():
            return f"ERROR: File not found: {file_path}"

        try:
            doc = fitz.open(str(path))
            metadata = doc.metadata

            info = [
                f"File: {path.name}",
                f"Pages: {len(doc)}",
                f"Title: {metadata.get('title') or 'N/A'}",
                f"Author: {metadata.get('author') or 'N/A'}",
                f"Subject: {metadata.get('subject') or 'N/A'}",
                f"Creator: {metadata.get('creator') or 'N/A'}",
                f"Creation Date: {metadata.get('creationDate') or 'N/A'}",
            ]

            doc.close()
            return "\n".join(info)

        except Exception as e:
            return f"ERROR getting PDF info: {str(e)}"
