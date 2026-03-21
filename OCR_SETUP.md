# OCR Setup Guide

This guide explains how to set up OCR (Optical Character Recognition) capabilities for the MARI Document System.

## Why OCR?

The system now extracts and stores **raw text** from documents **before** sending them to the LLM. This ensures:

✅ **Data preservation** - Text is stored even if LLM API fails  
✅ **Fallback capability** - Can retrieve basic text when rate-limited  
✅ **Debugging** - See exactly what text was extracted  
✅ **Cost savings** - Reduce LLM calls by caching OCR results  

## Installation Steps

### Step 1: Install Python Dependencies

```bash
pip install pytesseract pdf2image pillow
```

Or update your requirements:

```bash
pip install -r requirements.txt
```

### Step 2: Install Tesseract OCR Engine

Tesseract is required for pytesseract to work.

#### Windows Installation

1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (recommended location: `C:\Program Files\Tesseract-OCR`)
3. Add Tesseract to your PATH:
   - Open System Properties → Environment Variables
   - Add `C:\Program Files\Tesseract-OCR` to the Path variable
4. Verify installation:
   ```bash
   tesseract --version
   ```

#### Alternative: Using Chocolatey (Windows Package Manager)

```bash
choco install tesseract
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install libtesseract-dev
```

#### macOS

```bash
brew install tesseract
```

### Step 3: Install Poppler (for PDF support)

Required to convert PDF pages to images for OCR.

#### Windows

1. Download from: http://blog.alivate.com.au/poppler-windows/
2. Extract to `C:\Program Files\poppler`
3. Add `C:\Program Files\poppler\Library\bin` to your PATH

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install poppler-utils
```

#### macOS

```bash
brew install poppler
```

### Step 4: Run Database Migration

Add the new `raw_ocr_text` column to your database:

```bash
python migrate_add_ocr_column.py
```

## Testing OCR

Test that OCR is working:

```python
from app.services.ocr_provider import ocr_service

# Test with a sample file
with open("test.pdf", "rb") as f:
    file_data = f.read()

text = await ocr_service.extract_text(file_data, "application/pdf")
print(f"Extracted {len(text)} characters")
print(text[:500])  # Print first 500 chars
```

## How It Works Now

### Before (LLM-only):
```
Upload PDF → Send to Gemini → Store structured data
                          ↓
                    [429 Rate Limit]
                          ↓
                    ❌ NOTHING STORED
```

### After (OCR + LLM):
```
Upload PDF → Extract raw text (OCR) → Store in DB
              ↓
         Send to Gemini → Store structured data
                          ↓
                    [429 Rate Limit]
                          ↓
                    ✅ RAW TEXT SAVED
```

## Benefits

### 1. **Guaranteed Data Storage**
Even when Gemini API fails, you have the raw extracted text.

### 2. **Better Error Messages**
```json
{
  "status": "FAILED",
  "error": "LLM_RATE_LIMITED",
  "rawOcrText": "SEAFARER'S CERTIFICATE...\nName: John Doe\n...",
  "message": "Structured extraction failed, but raw text available"
}
```

### 3. **Future Enhancements**
- Use local OCR results for simple validations without calling LLM
- Cache OCR text to reduce LLM token usage
- Implement hybrid approach: OCR + smaller/faster LLM

## Troubleshooting

### Error: "Tesseract is not installed"

**Solution:** Make sure Tesseract is in your PATH:
```bash
where tesseract  # Windows
which tesseract  # Linux/Mac
```

### Error: "pdf2image requires poppler"

**Solution:** Install poppler (see Step 3 above)

### OCR returning empty text

**Possible causes:**
- Poor scan quality
- Handwritten text (Tesseract works best with printed text)
- Non-English documents (install language packs)

**Fix:** Install additional language packs:
```bash
# Example: Install Filipino language pack
# Windows: Download tessdata files from GitHub
# Linux: sudo apt-get install tesseract-ocr-fil
```

### Slow OCR processing

PDFs with many pages can be slow. Consider:
- Lowering DPI in `ocr_provider.py` (currently 300)
- Processing only first few pages
- Running OCR asynchronously

## Configuration

Edit OCR behavior in `app/services/ocr_provider.py`:

```python
# Change OCR language (default: English)
text = pytesseract.image_to_string(image, lang='eng')

# Adjust DPI for speed/accuracy tradeoff
images = convert_from_bytes(file_data, dpi=200)  # Lower = faster
```

## Performance

Typical processing times:
- Single page certificate: 2-5 seconds
- Multi-page document (10 pages): 15-30 seconds
- Depends on: page count, image quality, DPI setting

## Next Steps

1. ✅ Install dependencies
2. ✅ Run migration
3. ✅ Test with a sample document
4. ✅ Monitor logs for OCR extraction messages
5. 📊 Check database for `raw_ocr_text` field

## Example Usage

```bash
# Upload a document
curl -X POST 'http://localhost:8001/api/extract?mode=sync' \
  -F 'document=@PEME_Cruz_EXPIRED_FLAGS.pdf;type=application/pdf' \
  -F 'sessionId=test-session'

# Response will now include:
{
  "rawOcrText": "PROFESSIONAL EVALUATION...\nName: Cruz...\n..."
}
```

Even if the LLM fails, you'll see the extracted text!

---

**Questions?** Check the logs for messages like:
- `📝 Extracting raw text from...`
- `✅ Raw text extracted: X characters`
- `❌ LLM extraction failed, but OCR text may be available`
