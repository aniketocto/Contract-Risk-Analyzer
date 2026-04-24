import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# (Optional) Set this if OCR is used
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def ingestion_agent(file):
    try:
        file_path = file.name
        filename = file_path.lower()

        raw = ""

        # 📄 PDF
        if filename.endswith(".pdf"):
            doc = fitz.open(file_path)
            for page in doc:
                raw += page.get_text()
            doc.close()

        # 📃 TXT
        elif filename.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()

        # 🖼️ IMAGE (OCR)
        elif filename.endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(file_path)
            raw = pytesseract.image_to_string(image)

        else:
            return {"raw_text": "Unsupported file format"}

        
        cleaned = " ".join(raw.split())

        if not cleaned:
            return {"raw_text": "Error reading file"}

        return {"raw_text": cleaned}

    except Exception as e:
        return {"raw_text": f"Error reading file: {str(e)}"}


