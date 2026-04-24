import os
import re

# Heavy/optional deps (fitz, docx, PIL, pytesseract) imported lazily inside handlers

# Supported image extensions for OCR
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}


def _clean_text(raw: str) -> str:
    """
    Clean extracted text while PRESERVING line structure.

    The structuring agent depends on newlines to detect section headings
    like '3. Limitation of Liability' and 'Clause 3.1: ...'.
    We must NOT collapse everything into one line.

    What we DO clean:
      - Excessive blank lines (3+ → 2)
      - Trailing whitespace on each line
      - Leading/trailing whitespace on the whole text
      - Carriage returns
    """
    # Normalize line endings
    text = raw.replace('\r\n', '\n').replace('\r', '\n')

    # Remove trailing whitespace per line
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def ingestion_agent(file) -> dict:
    """
    Extract raw text from a contract file.

    Parameters
    ----------
    file : str, Path, or file-like object (Gradio/Streamlit upload)
        The contract file to ingest. Supports PDF, TXT, DOCX, and images.

    Returns
    -------
    dict with keys:
        - ``"raw_text"`` : extracted text (empty string on failure)
        - ``"filename"`` : original filename
        - ``"status"``   : "success" or "error"
        - ``"error"``    : error message (only present when status == "error")
    """
    try:
        # --- Resolve file path ---
        if isinstance(file, str):
            file_path = file
        elif hasattr(file, 'name'):
            file_path = file.name          # Gradio / Streamlit upload object
        else:
            file_path = str(file)          # pathlib.Path, etc.

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        if not os.path.exists(file_path):
            return {
                "raw_text": "",
                "filename": filename,
                "status": "error",
                "error": f"File not found: {file_path}",
            }

        raw = ""

        # ── PDF ──────────────────────────────────────────────────────
        if ext == ".pdf":
            try:
                import fitz  # PyMuPDF
            except ImportError:
                return {
                    "raw_text": "",
                    "filename": filename,
                    "status": "error",
                    "error": "PyMuPDF not installed. Run: pip install PyMuPDF",
                }
            doc = fitz.open(file_path)
            pages = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            # Join pages with double newline so page boundaries don't merge
            raw = "\n\n".join(pages)

        # ── Plain text ───────────────────────────────────────────────
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()

        # ── DOCX (Word) ─────────────────────────────────────────────
        elif ext == ".docx":
            try:
                import docx
            except ImportError:
                return {
                    "raw_text": "",
                    "filename": filename,
                    "status": "error",
                    "error": "python-docx not installed. Run: pip install python-docx",
                }
            document = docx.Document(file_path)
            raw = "\n".join(para.text for para in document.paragraphs)

        # ── Image (OCR) ─────────────────────────────────────────────
        elif ext in _IMAGE_EXTS:
            try:
                from PIL import Image
                import pytesseract
            except ImportError:
                return {
                    "raw_text": "",
                    "filename": filename,
                    "status": "error",
                    "error": "Pillow and pytesseract required for OCR. Run: pip install Pillow pytesseract",
                }
            image = Image.open(file_path)
            raw = pytesseract.image_to_string(image)

        # ── Unsupported ─────────────────────────────────────────────
        else:
            return {
                "raw_text": "",
                "filename": filename,
                "status": "error",
                "error": f"Unsupported file format: {ext}",
            }

        # ── Clean text (preserve newlines!) ──────────────────────────
        cleaned = _clean_text(raw)

        if not cleaned:
            return {
                "raw_text": "",
                "filename": filename,
                "status": "error",
                "error": "File appears to be empty or unreadable",
            }

        return {
            "raw_text": cleaned,
            "filename": filename,
            "status": "success",
        }

    except Exception as e:
        return {
            "raw_text": "",
            "filename": getattr(file, 'name', str(file)),
            "status": "error",
            "error": str(e),
        }
