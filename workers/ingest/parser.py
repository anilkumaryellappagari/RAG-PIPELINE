"""PDF text extraction using PyMuPDF."""

import pymupdf


def extract_pdf(pdf_path: str) -> dict:
    """Extract text from every page of a PDF."""

    document = pymupdf.open(pdf_path)

    try:
        pages = []

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                }
            )

        return {
            "page_count": len(document),
            "pages": pages,
        }

    finally:
        document.close()
