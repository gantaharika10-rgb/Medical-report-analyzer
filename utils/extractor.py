"""
Medical Report Text Extractor
Uses Groq Vision API for images (free, no quota issues)
Uses pdfplumber for PDFs (local)
"""

import os
import base64
import pdfplumber
from PIL import Image
from groq import Groq

# ── Configure Groq (free at https://console.groq.com) ───────────────────────


GROQ_API_KEY = os.environ["GROQ_API_KEY"]
groq_client = Groq(api_key=GROQ_API_KEY)

PROMPT = """You are a medical OCR system. Extract ALL text from this medical report image exactly as it appears.

Include:
- Patient name, age, sex, UHID
- Lab test names and results
- Reference ranges and units
- Status (Normal/High/Low/Abnormal)
- Doctor names, lab name, dates
- Any notes or comments
- Table data (preserve structure with spacing)

Ignore watermarks like lab background logos.
Return plain text only, preserving the layout as much as possible."""


def extract_text_from_image_groq(filepath: str) -> str:
    """Use Groq Vision to extract all text from a medical report image."""
    ext = filepath.rsplit('.', 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"

    with open(filepath, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    response = groq_client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{image_data}"}
                },
                {
                    "type": "text",
                    "text": PROMPT
                }
            ]
        }],
        max_tokens=2000
    )
    return response.choices[0].message.content.strip()


def extract_text_from_pdf(filepath: str):
    """Extract text from PDF using pdfplumber (local, no API needed)."""
    text = ""
    pages = 0
    with pdfplumber.open(filepath) as pdf:
        pages = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text, pages


def extract_text_from_file(filepath: str):
    """
    Main entry point called by app.py
    Returns: (text, pages, method)
    """
    ext = filepath.rsplit('.', 1)[-1].lower()

    # ── PDF: use pdfplumber (fast, local) ───────────────────────────────────
    if ext == 'pdf':
        text, pages = extract_text_from_pdf(filepath)
        if text.strip():
            return text, pages, "pdfplumber (local)"
        # Scanned PDF — convert to image and use Groq
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(filepath, first_page=1, last_page=1)
            temp_path = filepath + "_page1.jpg"
            images[0].save(temp_path, "JPEG")
            text = extract_text_from_image_groq(temp_path)
            os.remove(temp_path)
            return text, 1, "Groq Vision (scanned PDF)"
        except Exception as e:
            return text, pages, f"pdfplumber (partial: {e})"

    # ── Images: use Groq Vision ──────────────────────────────────────────────
    elif ext in ('png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp'):
        try:
            text = extract_text_from_image_groq(filepath)
            return text, 1, "Groq Vision API"
        except Exception as e:
            # Fallback to pytesseract if Groq fails
            try:
                import pytesseract
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
                return text, 1, f"Tesseract OCR (Groq failed: {e})"
            except Exception as e2:
                raise Exception(f"Both Groq and Tesseract failed: {e} | {e2}")

    else:
        raise Exception(f"Unsupported file type: {ext}")