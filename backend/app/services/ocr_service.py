from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRResult:
    def __init__(self, text: str, confidence: float, page_count: int = 1):
        self.text = text
        self.confidence = confidence
        self.page_count = page_count


class OCRService:
    def __init__(self):
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.warning("Tesseract not available, falling back to text extraction")
            return False

    async def extract_text_from_file(self, file_bytes: bytes, filename: str) -> OCRResult:
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return await self._extract_from_pdf(file_bytes)
        elif ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}:
            return await self._extract_from_image(file_bytes)
        elif ext in {".txt", ".text"}:
            text = file_bytes.decode("utf-8", errors="replace")
            return OCRResult(text=text, confidence=1.0)
        else:
            # Try PDF extraction as fallback
            try:
                return await self._extract_from_pdf(file_bytes)
            except Exception:
                text = file_bytes.decode("utf-8", errors="replace")
                return OCRResult(text=text, confidence=0.5)

    async def _extract_from_pdf(self, pdf_bytes: bytes) -> OCRResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_extract_pdf, pdf_bytes)

    def _sync_extract_pdf(self, pdf_bytes: bytes) -> OCRResult:
        texts = []
        page_count = 0

        # Try PyPDF2 first for text PDFs
        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
            for page in reader.pages:
                text = page.extract_text() or ""
                texts.append(text)
            combined = "\n".join(texts).strip()
            if len(combined) > 100:
                return OCRResult(text=combined, confidence=0.95, page_count=page_count)
        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")

        # Fallback to OCR via pdf2image + tesseract
        if self._tesseract_available:
            try:
                import pytesseract
                from pdf2image import convert_from_bytes

                images = convert_from_bytes(pdf_bytes, dpi=300)
                page_count = len(images)
                ocr_texts = []
                confidences = []

                for img in images:
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    words = [w for w, c in zip(data["text"], data["conf"]) if w.strip() and int(c) > 0]
                    confs = [int(c) for c in data["conf"] if int(c) > 0]
                    ocr_texts.append(" ".join(words))
                    if confs:
                        confidences.append(sum(confs) / len(confs))

                combined = "\n".join(ocr_texts).strip()
                avg_conf = sum(confidences) / len(confidences) / 100 if confidences else 0.5
                return OCRResult(text=combined, confidence=avg_conf, page_count=page_count)
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")

        return OCRResult(text="", confidence=0.0, page_count=page_count)

    async def _extract_from_image(self, image_bytes: bytes) -> OCRResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_extract_image, image_bytes)

    def _sync_extract_image(self, image_bytes: bytes) -> OCRResult:
        if not self._tesseract_available:
            return OCRResult(text="", confidence=0.0)

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            words = [w for w, c in zip(data["text"], data["conf"]) if w.strip() and int(c) > 0]
            confs = [int(c) for c in data["conf"] if int(c) > 0]
            text = " ".join(words)
            avg_conf = sum(confs) / len(confs) / 100 if confs else 0.5
            return OCRResult(text=text, confidence=avg_conf)
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return OCRResult(text="", confidence=0.0)


ocr_service = OCRService()
