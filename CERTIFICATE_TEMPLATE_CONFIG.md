# Certificate Template System Configuration

## Overview

The Certificate Template System allows administrators to upload custom certificate designs with placeholder tags (e.g., `{{name}}`, `{{distance}}`). The system uses OCR (Optical Character Recognition) to automatically detect tag positions and renders personalized certificates for participants.

---

## Image Requirements

### File Format
- **Accepted Formats**: PNG, JPG, JPEG
- **Recommended Format**: PNG (for transparency support and better quality)
- **Color Mode**: RGB or RGBA

### File Size
- **Maximum**: 15 MB
- **Recommended**: 2-5 MB (balances quality and upload speed)
- **Minimum**: No minimum, but ensure tags are readable

### Image Dimensions
- **Minimum**: 1920 x 1080 pixels (Full HD)
- **Maximum**: 8000 x 8000 pixels
- **Recommended**: 1920 x 1080 or 3840 x 2160 (4K)
- **Aspect Ratio**: 16:9 (landscape) recommended for certificate display

### Design Guidelines
- **Tag Visibility**: Use clear, readable fonts for `{{tag}}` placeholders
- **Font Size for Tags**: Minimum 24pt, recommended 36-48pt
- **Contrast**: High contrast between tag text and background (e.g., black text on light background)
- **Tag Format**: Must use double curly braces: `{{tag_name}}`
- **Avoid**: Overly stylized or cursive fonts for tags (OCR may fail to detect)

---

## 🎨 Professional Template Design Guidelines

### Critical Rules for OCR Detection

To ensure 100% reliable tag detection, follow these design principles when creating certificate templates:

#### 1. **Use Underscores Instead of Spaces in Tag Names** ⚠️ CRITICAL

❌ **WRONG**: `{{challenge name}}`, `{{digital signature}}`
✅ **CORRECT**: `{{challenge_name}}`, `{{digital_signature}}`

**Why**: OCR engines segment text by spaces, splitting `{{challenge name}}` into two separate bounding boxes:
- Box 1: `{{challenge`
- Box 2: `name}}`

This breaks geometric coordinate mapping and causes rendering failures.

**Solution**: Always use underscores for multi-word tags. The rendering engine will handle formatting automatically.

#### 2. **Use UPPERCASE Letters for Placeholder Tags** 🔤 HIGHLY RECOMMENDED

❌ **Suboptimal**: `{{challenge_name}}` (lowercase)
✅ **OPTIMAL**: `{{CHALLENGE_NAME}}` (uppercase)

**Why**: OCR engines read uppercase block letters with **significantly higher accuracy** than lowercase. Capital letters have sharp, distinct geometric features that machine learning models recognize easily.

**Note**: The final rendered certificate will use the user's specified font/case. The placeholder style doesn't affect aesthetics—it only affects machine readability.

#### 3. **Use High-Contrast Block Fonts for Placeholders** 📝 CRITICAL

❌ **WRONG**: Cursive/script fonts (Great Vibes, Pacifico, Dancing Script)
❌ **WRONG**: Decorative fonts with serifs or flourishes
✅ **CORRECT**: Bold sans-serif fonts (Arial Bold, Montserrat Black, Roboto Bold)

**Why**: Even though your final certificate may use beautiful cursive fonts for participant names, the **placeholder tags themselves** should be in blocky, machine-readable fonts.

**Example Template Design**:
```
Certificate of Achievement
Proudly presented to
{{NAME}}  ← Use Arial Bold 48pt (gets replaced with cursive font)
for completing
{{CHALLENGE_NAME}}  ← Use Montserrat Black 36pt
```

Since the rendering engine completely replaces the placeholder text, the aesthetic of the placeholder doesn't matter—only its machine readability matters.

#### 4. **Use Unique, Machine-Friendly Delimiters** 🔗 OPTIONAL

If double curly braces `{{}}` are getting misread as brackets or parentheses in your design, consider these alternative delimiters:

| Delimiter | Example | Benefit |
|-----------|---------|---------|
| **Hash symbols** | `#CHALLENGE_NAME#` | Rarely appears in decorative borders |
| **Angle brackets** | `<EVENT_NAME>` | Distinct from ornamental curves |
| **Double underscores** | `__DISTANCE__` | Clear separation from text |

**Backward Compatibility**: The system automatically normalizes all delimiters to standard `{{tag}}` format internally, so existing templates continue to work.

**Recommendation**: Stick with `{{TAG}}` unless you're experiencing OCR issues with your specific certificate design.

#### 5. **Avoid Decorative Borders Near Tag Text** 🖼️ IMPORTANT

**Problem**: Tesseract OCR treats intersecting decorative border lines (gold/blue ornamental patterns) as characters, generating phantom tags.

**Example Hallucination**: A decorative corner with crossing lines might be misread as `{{sport}}` or `{{signature}}`.

**Solutions**:
- **Keep 5% margin**: Place tags at least 5% away from image edges
- **Use solid backgrounds**: Place tags on solid color backgrounds, not over complex patterns
- **Increase contrast**: Ensure tag text has high contrast with its immediate background

#### 6. **Test Your Template Before Production** 🧪 ESSENTIAL

Before using a template for live events:

1. **Upload via Admin Panel**: Upload your template in the event form
2. **Review Detected Tags**: Check the "Detected Tags & Character Limits" section
3. **Verify Positions**: Click "Preview" to ensure tags are positioned correctly
4. **Reprocess if Needed**: Click "Reprocess OCR" if tags are misdetected
5. **Generate Test Certificate**: Create a test registration and download certificate

**Common Issues to Check**:
- ✅ All intended tags detected (no missing tags)
- ✅ No phantom/hallucinated tags (e.g., `{{sport}}` when not in template)
- ✅ Tag positions match visual layout
- ✅ Character limits are reasonable (see section below)

---

## Supported Tags

| Tag | Description | Example Value | Data Source |
|-----|-------------|---------------|-------------|
| `{{name}}` | Participant's full name | "John Doe" | `registration.participant_name` |
| `{{full_name}}` | Participant's full name (alias) | "John Doe" | `registration.participant_name` |
| `{{challenge_name}}` | Event/Challenge name | "Bicycle Day Run 2026" | `event.name` |
| `{{event_name}}` | Event name (alias) | "Bicycle Day Run 2026" | `event.name` |
| `{{distance}}` | Distance completed | "42.19 km" | `progress.distance_completed` |
| `{{date}}` | Completion date | "June 02, 2024" | `registration.confirmed_at` |
| `{{activity_name}}` | Activity type name | "5K Run" | `activity.name` |
| `{{sport}}` | Sport type | "running" | `activity.activity_type` |
| `{{certificate_number}}` | Unique certificate ID | "GLCG-2024-0031-00275" | `certificate.certificate_number` |
| `{{digital_signature}}` | Organization signature | "GlycoGrit Community Fitness Club" | Hardcoded constant |
| `{{registration_number}}` | Registration ID | "REG-2024-00456" | `registration.registration_number` |
| `{{bib_number}}` | Race bib number | "1234" | `registration.bib_number` |

---

## Technical Stack

### Backend Libraries

#### Core Dependencies
```python
# requirements.txt
pytesseract==0.3.10           # OCR for tag detection
opencv-python-headless==4.9.0.80  # Image preprocessing
Pillow==10.0.0                # Image manipulation and text rendering
httpx==0.24.1                 # Async HTTP client for template downloads
```

#### System Dependencies
```dockerfile
# Dockerfile
tesseract-ocr                 # OCR engine (Debian/Ubuntu)
tesseract-ocr-eng             # English language data
```

### Frontend Libraries
```typescript
// package.json (implicit via existing dependencies)
- fetch API (native)          // File upload
- FormData (native)           // Multipart requests
- React hooks                 // State management
```

---

## Storage Configuration

### Upload Destination
- **Service**: Cloudflare R2 (S3-compatible object storage)
- **Bucket**: Configured via environment variable `R2_BUCKET_NAME`
- **Region**: Auto (Cloudflare global network)

### Storage Paths

#### Template Storage
```
certificates/templates/event_{event_id}/template_{timestamp}_{uuid}.{ext}
```
**Example:**
```
certificates/templates/event_31/template_20260602_143022_a7b3c9d1.png
```

#### Generated Certificate Storage
```
certificates/generated/reg_{registration_id}/cert_{timestamp}_{uuid}.pdf
```
**Example:**
```
certificates/generated/reg_275/cert_20260602_150430_f8e2d4b6.pdf
```

### Storage Optimization
- **Templates**: NOT optimized (preserve quality for OCR)
- **Generated Certificates**: Optimized PDF (compressed)
- **Retention**: Permanent (no auto-deletion)
- **CDN**: Cloudflare CDN (automatic caching)

---

## Environment Variables

### Required Configuration

```bash
# Backend (.env)

# R2 Storage
R2_BUCKET_NAME=glycogrit-certificates
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_PUBLIC_URL=https://pub-xxxxx.r2.dev

# Database (for storing template config)
DATABASE_URL=postgresql://user:password@host:port/database

# OCR Settings (optional, defaults shown)
TESSERACT_CMD=tesseract                    # Path to tesseract binary
TESSERACT_LANG=eng                        # OCR language
OCR_CONFIDENCE_THRESHOLD=30               # Minimum confidence (0-100)
```

```bash
# Frontend (.env.production)

# API Base URL
VITE_API_BASE_URL=https://web-production-188d1.up.railway.app
```

### Optional Configuration

```bash
# Performance Tuning
CERTIFICATE_GENERATION_TIMEOUT=120000     # Timeout in ms (default: 2 minutes)
MAX_UPLOAD_SIZE=15728640                  # Max file size in bytes (default: 15MB)
TEMPLATE_MIN_WIDTH=1920                   # Minimum width in pixels
TEMPLATE_MIN_HEIGHT=1080                  # Minimum height in pixels

# Font Rendering
FONT_SCALE_MIN=0.80                       # Minimum font scale (80% of original)
FONT_SCALE_STEP=0.05                      # Scale reduction step (5%)
DEFAULT_FONT_FAMILY=Montserrat            # Fallback font
```

---

## Cost Analysis

### Storage Costs (Cloudflare R2)

#### Template Storage
- **Size per template**: ~2-5 MB
- **Cost**: $0.015 per GB/month
- **Example**: 100 templates = ~350 MB = **$0.01/month**

#### Generated Certificates
- **Size per certificate**: ~500 KB (PDF)
- **Cost**: $0.015 per GB/month
- **Example**: 10,000 certificates = ~5 GB = **$0.08/month**

#### Bandwidth (Class A Operations)
- **Template Upload**: $4.50 per million requests
- **Certificate Generation**: $4.50 per million requests
- **Download**: $0.36 per million requests
- **Example**: 1,000 uploads + 10,000 downloads = **~$0.05/month**

**Total Estimated Cost**: **$0.14/month** for 100 templates + 10,000 certificates

### Compute Costs (Railway)

#### OCR Processing
- **CPU Usage**: ~2-5 seconds per template upload
- **Memory**: ~200-500 MB per OCR operation
- **Cost**: Included in Railway plan (~$5-20/month depending on tier)

#### Certificate Generation
- **CPU Usage**: ~0.5-1 second per certificate
- **Memory**: ~100-200 MB per generation
- **Cost**: Included in Railway plan

---

## API Endpoints

### Upload Template (Admin Only)
```http
POST /api/v1/events/{event_id}/upload-certificate-template
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Body:
  file: <binary>
```

**Response:**
```json
{
  "template_url": "https://pub-xxx.r2.dev/certificates/templates/event_31/template_xxx.png",
  "detected_tags": [
    {
      "tag": "{{name}}",
      "display_name": "Participant Name",
      "bbox": { "x": 500, "y": 300, "width": 920, "height": 80 },
      "font_size": 48,
      "font_color": "#000000",
      "alignment": "center",
      "confidence": 0.85
    }
  ],
  "template_config": { ... },
  "message": "Template uploaded successfully. Detected 5 tags."
}
```

### Download Certificate (User)
```http
GET /api/v1/certificates/registration/{registration_id}/download
Authorization: Bearer {user_token}
```

**Response:** PDF file (binary stream)

---

## Database Schema

### Events Table Extensions
```sql
ALTER TABLE events ADD COLUMN certificate_template_url VARCHAR(500);
ALTER TABLE events ADD COLUMN certificate_template_config JSONB;
ALTER TABLE events ADD COLUMN uses_custom_template BOOLEAN DEFAULT FALSE;
```

### Template Config Structure (JSONB)
```json
{
  "template_dimensions": {
    "width": 1920,
    "height": 1080,
    "format": "PNG"
  },
  "detected_tags": [
    {
      "tag": "{{name}}",
      "display_name": "Participant Name",
      "bbox": { "x": 500, "y": 300, "width": 920, "height": 80 },
      "font_size": 48,
      "font_color": "#000000",
      "font_family": "Montserrat",
      "alignment": "center",
      "confidence": 0.85
    }
  ],
  "ocr_performed_at": "2026-06-02T12:00:00.000000",
  "ocr_version": "pytesseract-0.3.10"
}
```

---

## Processing Pipeline

### 1. Template Upload Flow
```
Admin uploads template
    ↓
Validate file (format, size, dimensions)
    ↓
Upload to R2 (preserve original quality)
    ↓
Preprocess image (grayscale, adaptive threshold, denoise)
    ↓
Run Tesseract OCR (detect {{tags}})
    ↓
Estimate font properties (size, color, alignment)
    ↓
Store config in database (JSONB)
    ↓
Return detected tags to admin
```

### 2. Certificate Generation Flow
```
User requests certificate download
    ↓
Check if event uses custom template
    ↓
IF template exists:
    Download template from R2
    Load user data (name, distance, date, etc.)
    For each detected tag:
        - Get user value
        - Load font (TrueType)
        - Auto-scale if text too wide (min 80%)
        - Render text on template
    Convert to PDF
    Upload to R2
    Return PDF URL
ELSE:
    Generate HTML certificate (fallback)
    Convert to PDF with WeasyPrint
    Upload to R2
    Return PDF URL
```

---

## Bundled Fonts

### Font Assets Location
```
app/assets/fonts/
├── Montserrat-Regular.ttf
├── Montserrat-Bold.ttf
├── PlayfairDisplay-Regular.ttf
├── PlayfairDisplay-Bold.ttf
├── GreatVibes-Regular.ttf
└── LICENSE.txt
```

### Font Selection
1. **Montserrat** (Sans-serif): Modern, clean look for names/body text
2. **Playfair Display** (Serif): Elegant, formal for titles
3. **Great Vibes** (Script): Handwritten style for signatures

### License
All fonts: **SIL Open Font License 1.1** (free for commercial use)

---

## Error Handling

### Template Upload Errors

| Error | Cause | Solution |
|-------|-------|----------|
| **"Template too small"** | Dimensions < 1920x1080 | Resize image to minimum dimensions |
| **"Unsupported format"** | File is not PNG/JPG | Convert to PNG or JPG |
| **"File size exceeds 15MB"** | File > 15MB | Compress image or reduce dimensions |
| **"No tags detected"** | OCR couldn't find `{{tags}}` | Use clear, readable fonts; ensure high contrast |
| **"Tesseract not installed"** | System dependency missing | Install `tesseract-ocr` on server |

### Certificate Generation Errors

| Error | Cause | Fallback |
|-------|-------|----------|
| **Template download fails** | R2 unavailable | Use HTML generation |
| **Font loading fails** | Font file missing | Use PIL default font |
| **Text overflow** | Name too long | Scale font down to 80% minimum |
| **OCR config missing** | Database corruption | Re-upload template |

---

## Performance Benchmarks

### OCR Processing
- **Time**: 2-5 seconds (depends on image size)
- **Memory**: 200-500 MB peak
- **CPU**: Single core, 100% utilization during OCR

### Certificate Generation
- **Time**: 0.5-1.5 seconds per certificate
- **Memory**: 100-200 MB peak
- **CPU**: Single core, 80% utilization

### Concurrency
- **Async Support**: Yes (FastAPI async endpoints)
- **Max Concurrent Uploads**: 10 (recommended)
- **Max Concurrent Generations**: 50 (recommended)

---

## Future Improvements & TODOs

### High Priority
- [ ] **Certificate Preview**: Allow admin to preview certificate with sample data before publishing
- [ ] **Batch Generation**: Generate certificates for all event participants at once
- [ ] **QR Code Verification**: Add QR code to certificates for authenticity verification
- [ ] **Template Versioning**: Keep history of template changes
- [ ] **A/B Testing**: Test multiple templates and track download rates

### Medium Priority
- [ ] **Multi-Language Support**: Detect and support non-English tags
- [ ] **Custom Tag Definitions**: Allow admin to define custom tags beyond predefined set
- [ ] **Font Upload**: Allow admin to upload custom fonts for rendering
- [ ] **Template Gallery**: Pre-built templates library for admins
- [ ] **Responsive Certificates**: Auto-resize for mobile viewing

### Low Priority
- [ ] **Watermark Support**: Add optional watermarks
- [ ] **Social Media Sharing**: One-click share to Instagram/Facebook
- [ ] **Email Integration**: Auto-email certificates to participants
- [ ] **Analytics Dashboard**: Track certificate downloads and engagement
- [ ] **Template Marketplace**: Share/sell templates between organizations

### Technical Debt
- [ ] **Unit Tests**: Add tests for OCR detection and text rendering
- [ ] **Integration Tests**: End-to-end tests for upload → generate → download
- [ ] **Error Recovery**: Retry logic for transient R2 failures
- [ ] **Rate Limiting**: Prevent abuse of upload endpoint
- [ ] **Monitoring**: Add metrics for OCR accuracy and generation time

---

## Troubleshooting Guide

### Issue: OCR Not Detecting Tags

**Symptoms:**
- Upload succeeds but returns "No tags detected"
- Response shows empty `detected_tags` array

**Solutions:**
1. **Check tag format**: Must be `{{tag}}` not `{tag}` or `[[tag]]`
2. **Increase contrast**: Use black text on white/light background
3. **Use simpler fonts**: Avoid cursive, script, or highly stylized fonts
4. **Increase font size**: Use minimum 24pt, recommended 36-48pt
5. **Check image quality**: Ensure image is not blurry or low resolution

### Issue: Text Overflowing Bounding Box

**Symptoms:**
- Certificate shows truncated names
- Console warning: "Text doesn't fit even at minimum scale"

**Solutions:**
1. **Increase bbox width**: Make tag placeholder area wider in template
2. **Use shorter display names**: Encourage users to use shorter names
3. **Adjust MIN_FONT_SCALE**: Change from 0.80 to 0.70 (70% minimum)

### Issue: Certificate Generation Timeout

**Symptoms:**
- Error: "Certificate generation timed out"
- 504 Gateway Timeout

**Solutions:**
1. **Increase timeout**: Change `CERTIFICATE_GENERATION_TIMEOUT` to 180000 (3 min)
2. **Optimize template**: Use smaller template images (< 3 MB)
3. **Scale infrastructure**: Upgrade Railway plan for more CPU/memory

---

## Security Considerations

### Access Control
- **Template Upload**: Admin-only (role check at API level)
- **Certificate Download**: User must be authenticated and own the registration
- **Template URL**: Public (R2 CDN) but non-guessable UUIDs

### Input Validation
- **File Type**: Whitelist PNG/JPG only (MIME type verification)
- **File Size**: Hard limit at 15 MB
- **Dimensions**: Validate min/max dimensions
- **SQL Injection**: Parameterized queries (SQLAlchemy ORM)
- **XSS**: No user input rendered in HTML (PDF only)

### Data Privacy
- **Participant Names**: Stored in database, rendered on certificates
- **PII Protection**: No SSN, credit card, or sensitive data on certificates
- **GDPR Compliance**: Certificates can be deleted on request
- **Data Retention**: Certificates stored indefinitely unless user requests deletion

---

## Monitoring & Logging

### Key Metrics to Track
- **Upload Success Rate**: % of template uploads that succeed
- **OCR Accuracy**: Average number of tags detected per template
- **Generation Time**: P50, P95, P99 latency for certificate generation
- **Storage Usage**: Total GB used for templates and certificates
- **Error Rate**: % of certificate generations that fail

### Log Levels
```python
# template_service.py
logger.info("✅ Template processed successfully")
logger.warning("⚠️  Text doesn't fit at minimum scale")
logger.error("❌ OCR detection failed")
```

### Recommended Monitoring Tools
- **Sentry**: Error tracking and performance monitoring
- **Datadog**: Infrastructure metrics and APM
- **CloudWatch**: Railway logs aggregation
- **Grafana**: Custom dashboards for certificate metrics

---

## Support & Maintenance

### Regular Maintenance Tasks
1. **Monthly**: Review storage costs and optimize if needed
2. **Quarterly**: Update OCR confidence threshold based on accuracy metrics
3. **Yearly**: Update font library with new designs

### Support Contacts
- **Tesseract Issues**: https://github.com/tesseract-ocr/tesseract/issues
- **Pillow Issues**: https://github.com/python-pillow/Pillow/issues
- **R2 Issues**: Cloudflare support portal

---

## References

### Documentation
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **Pillow (PIL)**: https://pillow.readthedocs.io/
- **Cloudflare R2**: https://developers.cloudflare.com/r2/
- **FastAPI**: https://fastapi.tiangolo.com/

### Source Code Locations
- **Backend**:
  - Template Service: `app/modules/certificates/services/template_service.py`
  - Template Processor: `app/modules/certificates/services/template_processor.py`
  - Storage Service: `app/modules/gallery/services/storage_service.py`
  - API Endpoint: `app/modules/events/api/events.py`
- **Frontend**:
  - Event Form: `src/pages/EventForm.tsx`
  - API Client: `src/lib/api-client.ts`
- **Database**:
  - Migration: `alembic/versions/20260602_add_certificate_template_fields.py`
  - Event Model: `app/modules/events/domain/event.py`

---

## 🚀 Future OCR Engine Migration Strategy

### Current Implementation: Tesseract OCR

**Strengths**:
- ✅ Free and open-source (Apache 2.0 license)
- ✅ No API costs or rate limits
- ✅ Works offline (no external dependencies)
- ✅ Lightweight and fast

**Limitations**:
- ❌ Struggles with cursive/decorative fonts
- ❌ Hallucinates tags from border intersections
- ❌ Requires high-contrast, blocky fonts for accuracy
- ❌ Relies on traditional contour analysis (not deep learning)

### Recommended Next-Generation Engines

#### Option A: **EasyOCR** (Most Recommended)

**What it is**: Deep learning-based OCR built on PyTorch using CRAFT text detector and CRNN recognizer.

**Why it's ideal for certificates**:
- ✅ **Scene text optimized**: Designed for complex backgrounds, stylized fonts, certificates
- ✅ **Border-resistant**: Uses text-like texture detection instead of high-contrast lines
- ✅ **Multi-language support**: 80+ languages out of the box
- ✅ **No hallucinations**: Deep learning models don't confuse decorative borders with text

**Installation**:
```bash
pip install easyocr
```

**Integration Example**:
```python
import easyocr

reader = easyocr.Reader(['en'], gpu=False)  # CPU mode for Railway
result = reader.readtext(img_array, detail=1)

for (bbox, text, conf) in result:
    # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    # No need for extensive normalization!
```

**License**: Apache 2.0 (Free & Open Source)

**Migration Effort**: ~2-4 hours (swap OCR backend, test, deploy)

#### Option B: **PaddleOCR**

**What it is**: Industrial-grade OCR toolkit by Baidu with state-of-the-art layout analysis.

**Why it's ideal for certificates**:
- ✅ **Best-in-class accuracy**: Highest precision bounding boxes
- ✅ **Multi-oriented text**: Handles rotated or curved text
- ✅ **Layout analysis**: Understands document structure
- ✅ **Production-proven**: Used by Fortune 500 companies

**Installation**:
```bash
pip install paddlepaddle paddleocr
```

**Integration Example**:
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='en')
result = ocr.ocr(img_array, cls=True)

for line in result[0]:
    bbox, (text, conf) = line
    # Highly precise bounding boxes!
```

**License**: Apache 2.0 (Free & Open Source)

**Migration Effort**: ~3-5 hours (slightly more complex API)

### Migration Checklist

When ready to migrate from Tesseract:

- [ ] Add `easyocr` or `paddleocr` to `requirements.txt`
- [ ] Update `_perform_ocr_detection()` in `template_service.py`
- [ ] Remove Tesseract-specific normalization (bracket fixes, border filters)
- [ ] Test with existing templates (should work without changes)
- [ ] Deploy to staging environment
- [ ] Run A/B comparison: Tesseract vs. new engine
- [ ] Update documentation with new OCR engine details

### Backward Compatibility

**No template changes required!** The new engines will work with existing templates because:
- ✅ Tag format remains the same (`{{tag}}`, `#TAG#`, etc.)
- ✅ Bounding box format is compatible
- ✅ User-facing API doesn't change (upload → detect → render)

**Admins simply click "Reprocess OCR"** to re-analyze templates with the new engine.

---

**Last Updated**: June 3, 2026
**Version**: 1.1.0
**Author**: GlycoGrit Development Team
