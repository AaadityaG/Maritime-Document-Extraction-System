"""OCR service for extracting text from documents"""

import io
from typing import Optional
from PIL import Image

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCRService:
    """Service for extracting raw text from documents using OCR"""
    
    def __init__(self):
        if not TESSERACT_AVAILABLE:
            print("⚠️  WARNING: Tesseract/Pytesseract not installed. OCR features disabled.")
            print("   Install with: pip install pytesseract pdf2image")
            print("   Also need Tesseract OCR engine: https://github.com/tesseract-ocr/tesseract")
    
    async def extract_text(
        self,
        file_data: bytes,
        mime_type: str
    ) -> Optional[str]:
        """
        Extract raw text from document using OCR.
        
        Args:
            file_data: Raw file bytes
            mime_type: MIME type of the file
            
        Returns:
            Extracted text or None if extraction fails
        """
        if not TESSERACT_AVAILABLE:
            return None
        
        try:
            if mime_type == "application/pdf":
                return await self._extract_from_pdf(file_data)
            elif mime_type in ["image/jpeg", "image/png"]:
                return await self._extract_from_image(file_data)
            else:
                # Try as image anyway
                return await self._extract_from_image(file_data)
        except Exception as e:
            print(f"❌ OCR extraction failed: {str(e)}")
            return None
    
    async def _extract_from_pdf(self, file_data: bytes) -> Optional[str]:
        """Extract text from PDF by converting pages to images"""
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(file_data, dpi=300)
            
            all_text = []
            for i, image in enumerate(images):
                page_text = await self._extract_from_image_bytes(image)
                if page_text:
                    all_text.append(f"--- Page {i+1} ---\n{page_text}")
            
            return "\n\n".join(all_text) if all_text else None
            
        except Exception as e:
            print(f"PDF OCR failed: {str(e)}")
            return None
    
    async def _extract_from_image(self, file_data: bytes) -> Optional[str]:
        """Extract text from image file"""
        try:
            image = Image.open(io.BytesIO(file_data))
            return await self._extract_from_image_bytes(image)
        except Exception as e:
            print(f"Image OCR failed: {str(e)}")
            return None
    
    async def _extract_from_image_bytes(self, image: Image.Image) -> Optional[str]:
        """Extract text from PIL Image"""
        try:
            # Use tesseract to extract text
            # You can specify lang parameter for different languages
            text = pytesseract.image_to_string(image, lang='eng')
            return text.strip() if text else None
        except Exception as e:
            print(f"Tesseract extraction failed: {str(e)}")
            return None


# Global instance
ocr_service = OCRService()
