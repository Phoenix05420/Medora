"""
Smart Medical OCR Service — Triple-Engine Local Pipeline
Engines: PaddleOCR (primary) + EasyOCR (secondary) + Tesseract (tertiary)
All processing is done locally — no cloud APIs required.
"""

import os
import cv2
import numpy as np
import logging
import re
import json
from difflib import get_close_matches
from pathlib import Path

# Configure structured logging
logger = logging.getLogger("ocr_service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[OCR] %(levelname)s — %(message)s"))
    logger.addHandler(handler)

# ── Engine Imports (graceful degradation) ────────────────────────────────────
_paddle_available = False
_easyocr_available = False
_tesseract_available = False

try:
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    from paddleocr import PaddleOCR
    _paddle_available = True
    logger.info("PaddleOCR engine available")
except ImportError:
    logger.warning("PaddleOCR not installed — skipping engine.")

try:
    import easyocr
    _easyocr_available = True
    logger.info("EasyOCR engine available")
except ImportError:
    logger.warning("EasyOCR not installed — skipping engine.")

try:
    import pytesseract
    _tesseract_available = True
except ImportError:
    logger.warning("pytesseract not installed — skipping engine.")


class OcrService:
    """Triple-engine local OCR with advanced preprocessing and medical parsing."""

    def __init__(self, tesseract_path=None):
        # ── Local Engines (Lazy Loading) ──
        self.paddle = None
        self.easy_reader = None
        self._tesseract_verified = False

        # ── Tesseract Configuration ──
        if _tesseract_available:
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            try:
                pytesseract.get_tesseract_version()
                self._tesseract_verified = True
                logger.info(f"Tesseract configured (path: {tesseract_path or 'system default'})")
            except Exception:
                logger.warning("pytesseract installed but Tesseract binary not found")

        # Keep gemini_client as None so summary.py doesn't crash
        self.gemini_client = None

        # ── Medicine Database (for fuzzy matching) ──
        self.medicine_list = []
        try:
            db_path = Path(__file__).parent / "medicine_db.json"
            if db_path.exists():
                with open(db_path, "r") as f:
                    self.medicine_list = json.load(f).get("medicines", [])
                logger.info(f"Medicine Database loaded ({len(self.medicine_list)} records)")
        except Exception as e:
            logger.error(f"Failed to load medicine database: {e}")

        engines = []
        if _paddle_available: engines.append("PaddleOCR")
        if _easyocr_available: engines.append("EasyOCR")
        if self._tesseract_verified: engines.append("Tesseract")
        logger.info(f"OCR Service initialized — Engines: {', '.join(engines) or 'NONE'}")

    # ═══════════════════════════════════════════════════════════════════════════
    #  IMAGE PREPROCESSING PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════

    def preprocess(self, image_path):
        """Full preprocessing pipeline for medical documents."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        h, w = img.shape[:2]
        max_dim = 2000
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.bilateralFilter(enhanced, 11, 85, 85)
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11, C=2
        )
        binary = self._deskew(binary)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        return img, cleaned

    def _deskew(self, image):
        """Auto-correct document rotation."""
        try:
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                     minLineLength=100, maxLineGap=10)
            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    if abs(angle) < 15:
                        angles.append(angle)
                if angles:
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.5:
                        h, w = image.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        image = cv2.warpAffine(image, M, (w, h),
                                                flags=cv2.INTER_CUBIC,
                                                borderMode=cv2.BORDER_REPLICATE)
        except Exception as e:
            logger.warning(f"Deskew failed (non-critical): {e}")
        return image

    # ═══════════════════════════════════════════════════════════════════════════
    #  TRIPLE-ENGINE OCR (Local Only)
    # ═══════════════════════════════════════════════════════════════════════════

    def get_text(self, image_path):
        """Run all three local OCR engines and fuse results."""
        results = {
            "doctor_name": "Not detected",
            "medicines": [],
            "diagnoses": [],
            "raw_text": "",
            "confidence": 0.0,
            "engines_used": []
        }

        converted_path = None

        try:
            # Convert unsupported formats to PNG
            ext = Path(image_path).suffix.lower()
            supported_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.pdf'}
            if ext not in supported_exts:
                logger.info(f"Converting '{ext}' to PNG...")
                from PIL import Image
                pil_img = Image.open(image_path)
                converted_path = image_path + "_converted.png"
                pil_img.save(converted_path, "PNG")
                image_path = converted_path

            original_img, preprocessed_img = self.preprocess(image_path)

            # Save preprocessed image for engines that need a file path
            prep_path = image_path + "_preprocessed.png"
            cv2.imwrite(prep_path, preprocessed_img)

            # ── Engine 1: PaddleOCR ──
            paddle_lines = self._run_paddle(image_path)

            # ── Engine 2: EasyOCR ──
            easy_lines = self._run_easyocr(prep_path)

            # ── Engine 3: Tesseract ──
            tess_lines = self._run_tesseract(preprocessed_img)

            # ── Intelligent Fusion ──
            fused_text = self._fuse_results(paddle_lines, easy_lines, tess_lines)
            results["raw_text"] = fused_text

            # Calculate average confidence
            all_scores = [l[1] for src in [paddle_lines, easy_lines, tess_lines] for l in src if l[1] > 0]
            results["confidence"] = round(sum(all_scores) / len(all_scores) * 100, 1) if all_scores else 0.0
            results["engines_used"] = [
                e for e, lines in [("PaddleOCR", paddle_lines), ("EasyOCR", easy_lines), ("Tesseract", tess_lines)]
                if lines
            ]

            # ── Medical Data Extraction ──
            self._parse_medical_data(fused_text, results)

            logger.info(
                f"OCR complete — {len(results['medicines'])} meds found, "
                f"{results['confidence']}% avg confidence, "
                f"engines: {', '.join(results['engines_used'])}"
            )

            # Cleanup temp files
            if os.path.exists(prep_path):
                os.remove(prep_path)
            if converted_path and os.path.exists(converted_path):
                os.remove(converted_path)

        except Exception as e:
            logger.error(f"OCR Pipeline Error: {e}")
            results["raw_text"] = f"Error processing image: {str(e)}"
            if converted_path and os.path.exists(converted_path):
                os.remove(converted_path)

        return results

    def _run_paddle(self, image_path):
        """Lazy-loaded PaddleOCR engine."""
        if not _paddle_available:
            return []
        try:
            if self.paddle is None:
                logger.info("Loading PaddleOCR...")
                self.paddle = PaddleOCR(use_textline_orientation=False, enable_mkldnn=False, lang='en')

            res = self.paddle.ocr(image_path)
            if res and len(res) > 0 and res[0]:
                lines = []
                for line in res[0]:
                    text, score = line[1]
                    lines.append((text, score))
                logger.info(f"PaddleOCR: {len(lines)} lines")
                return lines
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
        return []

    def _run_easyocr(self, image_path):
        """Lazy-loaded EasyOCR engine."""
        if not _easyocr_available:
            return []
        try:
            if self.easy_reader is None:
                logger.info("Loading EasyOCR (CPU mode)...")
                self.easy_reader = easyocr.Reader(['en'], gpu=False, verbose=False)

            results = self.easy_reader.readtext(image_path)
            lines = [(text, conf) for (_, text, conf) in results]
            logger.info(f"EasyOCR: {len(lines)} lines")
            return lines
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
        return []

    def _run_tesseract(self, preprocessed_img):
        """Tesseract engine — returns list of (text, confidence) tuples."""
        if not self._tesseract_verified:
            return []
        try:
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(preprocessed_img, config=custom_config)
            lines = [(line.strip(), 0.7) for line in text.split('\n') if line.strip()]
            logger.info(f"Tesseract: {len(lines)} lines")
            return lines
        except Exception as e:
            logger.error(f"Tesseract error: {e}")
        return []

    # ═══════════════════════════════════════════════════════════════════════════
    #  INTELLIGENT FUSION
    # ═══════════════════════════════════════════════════════════════════════════

    def _fuse_results(self, paddle_lines, easy_lines, tess_lines):
        """
        Intelligent multi-engine text fusion.
        Strategy: Prioritize by confidence, deduplicate similar lines.
        """
        all_lines = []
        for text, conf in paddle_lines:
            all_lines.append((text.strip(), conf, "paddle"))
        for text, conf in easy_lines:
            all_lines.append((text.strip(), conf, "easy"))
        for text, conf in tess_lines:
            all_lines.append((text.strip(), conf, "tess"))

        if not all_lines:
            return ""

        # Deduplicate: if two lines are >80% similar, keep the higher-confidence one
        unique_lines = []
        for text, conf, src in all_lines:
            if not text or len(text) < 2:
                continue
            is_duplicate = False
            for i, (existing_text, existing_conf, _) in enumerate(unique_lines):
                similarity = self._text_similarity(text.lower(), existing_text.lower())
                if similarity > 0.8:
                    is_duplicate = True
                    if conf > existing_conf:
                        unique_lines[i] = (text, conf, src)
                    break
            if not is_duplicate:
                unique_lines.append((text, conf, src))

        best_source_lines = sorted(unique_lines, key=lambda x: -x[1])
        return "\n".join([line[0] for line in best_source_lines])

    @staticmethod
    def _text_similarity(a, b):
        """Simple word-level Jaccard similarity."""
        if not a or not b:
            return 0.0
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    # ═══════════════════════════════════════════════════════════════════════════
    #  MEDICAL DATA EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════════

    MEDICINE_DB = {
        "amlodipine", "atenolol", "bisoprolol", "carvedilol", "diltiazem",
        "enalapril", "lisinopril", "losartan", "metoprolol", "nifedipine",
        "propranolol", "ramipril", "telmisartan", "valsartan", "verapamil",
        "clopidogrel", "warfarin", "rivaroxaban", "apixaban", "aspirin",
        "furosemide", "hydrochlorothiazide", "spironolactone", "digoxin",
        "metformin", "glimepiride", "gliclazide", "sitagliptin", "empagliflozin",
        "dapagliflozin", "pioglitazone", "insulin", "semaglutide",
        "atorvastatin", "rosuvastatin", "simvastatin", "fenofibrate", "ezetimibe",
        "omeprazole", "pantoprazole", "esomeprazole", "lansoprazole",
        "rabeprazole", "ranitidine", "famotidine", "domperidone", "ondansetron",
        "paracetamol", "acetaminophen", "ibuprofen", "diclofenac",
        "naproxen", "celecoxib", "piroxicam", "tramadol",
        "morphine", "fentanyl", "oxycodone", "codeine",
        "pregabalin", "gabapentin", "amitriptyline",
        "amoxicillin", "ampicillin", "penicillin",
        "azithromycin", "erythromycin", "clarithromycin",
        "ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin",
        "doxycycline", "tetracycline", "cephalexin", "cefuroxime",
        "cefixime", "ceftriaxone", "metronidazole", "nitrofurantoin",
        "fluconazole", "itraconazole", "clotrimazole", "acyclovir",
        "salbutamol", "ipratropium", "budesonide", "fluticasone",
        "montelukast", "cetirizine", "levocetirizine", "loratadine",
        "fexofenadine", "chlorpheniramine", "diphenhydramine",
        "prednisone", "prednisolone", "dexamethasone", "hydrocortisone",
        "sertraline", "escitalopram", "fluoxetine", "venlafaxine",
        "alprazolam", "diazepam", "lorazepam", "clonazepam",
        "olanzapine", "quetiapine", "risperidone", "haloperidol",
        "valproate", "carbamazepine", "lamotrigine", "levetiracetam", "phenytoin",
        "levothyroxine", "methotrexate", "hydroxychloroquine",
        "multivitamin", "calcium", "vitamin", "folic", "ferrous",
        "iron", "zinc", "magnesium", "cholecalciferol",
        "sildenafil", "tamsulosin", "allopurinol", "colchicine",
    }

    def _parse_medical_data(self, text, results):
        """Extract structured medical data from raw OCR text."""

        # ── Doctor Name ──
        doc_patterns = [
            r"(?:Dr\.|Doctor|Physician)\.?\s+([A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2})",
            r"(?:Consultant|Prescribed\s+by):?\s+([A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2})",
        ]
        for p in doc_patterns:
            match = re.search(p, text, re.I)
            if match:
                results["doctor_name"] = match.group(1).strip()
                break

        # ── Visit Date ──
        date_patterns = [
            r"(?:Date|Visit|Dated?):?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        ]
        for p in date_patterns:
            match = re.search(p, text, re.I)
            if match:
                results["visit_date"] = match.group(1).strip()
                break

        # ── Diagnosis ──
        diag_patterns = [
            r"(?:Diagnosis|Dx|Impression|Assessment|Condition):?\s*(.+?)(?:\n|$)",
            r"(?:Complain(?:t|ts)|C/O|Chief\s+Complaint):?\s*(.+?)(?:\n|$)",
        ]
        diagnoses = []
        for p in diag_patterns:
            matches = re.findall(p, text, re.I)
            for m in matches:
                d = m.strip().rstrip('.,;:')
                if d and len(d) > 3 and d not in diagnoses:
                    diagnoses.append(d)
        if diagnoses:
            results["diagnoses"] = diagnoses

        # ── Medication Extraction ──
        dosage_regex = r"(\d+\.?\d*\s*(?:mg|ml|mcg|g|tablet|tab|cap|capsule|units|iu|%|drops?|puff|spray))"
        frequency_regex = r"(\d+-\d+-\d+|\d+\s*(?:times?\s*(?:a|per)\s*day|x\s*daily)|[Oo]nce|[Tt]wice|BD|TDS|TID|QD|QID|OD|HS|PRN|SOS|stat|daily|weekly|morning|evening|night|bedtime|before\s+meals?|after\s+meals?|AC|PC|BBF)"
        duration_regex = r"(?:for|x|=)?\s*(\d+\s*(?:days?|weeks?|months?|wks?|mos?))"
        route_regex = r"\b(oral|topical|IV|IM|SC|sublingual|inhaler|nebulizer|rectal|PO|PR|nasal|transdermal|ophthalmic|otic|vaginal|inhalation)\b"

        lines = text.split('\n')
        for line in lines:
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 4:
                continue

            # Strategy 1: Dosage-anchor extraction
            dosage_match = re.search(dosage_regex, line_clean, re.I)
            if dosage_match:
                pre_text = line_clean[:dosage_match.start()].strip()
                pre_text = re.sub(r'^[\d\.\)\-\*\#]+\s*', '', pre_text).strip()
                name_match = re.search(r'([A-Za-z][A-Za-z\s\-]+)$', pre_text)
                med_name = name_match.group(1).strip() if name_match else pre_text

                if med_name and len(med_name) > 2:
                    corrected_name, is_validated = self._fuzzy_match_medicine(med_name)
                    post_text = line_clean[dosage_match.end():].strip()
                    freq_match = re.search(frequency_regex, post_text, re.I)
                    dur_match = re.search(duration_regex, post_text, re.I)
                    route_match = re.search(route_regex, line_clean, re.I)

                    med_entry = {
                        "name": corrected_name,
                        "dosage": dosage_match.group(1).strip(),
                        "frequency": freq_match.group(1).strip() if freq_match else "As directed",
                        "duration": dur_match.group(1).strip() if dur_match else "Not specified",
                        "route": route_match.group(1).strip() if route_match else "",
                        "validated": is_validated,
                    }
                    if not any(m['name'].lower() == corrected_name.lower() for m in results["medicines"]):
                        results["medicines"].append(med_entry)
                    continue

            # Strategy 2: Known medicine name lookup
            for word in line_clean.split():
                clean_word = word.strip('.,;:()[]')
                if len(clean_word) < 3:
                    continue
                corrected, is_match = self._fuzzy_match_medicine(clean_word)
                if is_match:
                    dosage_in_line = re.search(dosage_regex, line_clean, re.I)
                    freq_in_line = re.search(frequency_regex, line_clean, re.I)
                    dur_in_line = re.search(duration_regex, line_clean, re.I)
                    route_in_line = re.search(route_regex, line_clean, re.I)
                    med_entry = {
                        "name": corrected,
                        "dosage": dosage_in_line.group(1).strip() if dosage_in_line else "See prescription",
                        "frequency": freq_in_line.group(1).strip() if freq_in_line else "As directed",
                        "duration": dur_in_line.group(1).strip() if dur_in_line else "Not specified",
                        "route": route_in_line.group(1).strip() if route_in_line else "",
                        "validated": True,
                    }
                    if not any(m['name'].lower() == corrected.lower() for m in results["medicines"]):
                        results["medicines"].append(med_entry)
                    break

    def _fuzzy_match_medicine(self, name):
        """Match a medicine name against the database with fuzzy matching."""
        lower = name.lower().strip()
        if lower in self.MEDICINE_DB:
            return name.capitalize(), True
        first_word = lower.split()[0] if lower.split() else lower
        if first_word in self.MEDICINE_DB:
            return first_word.capitalize(), True
        matches = get_close_matches(lower, self.MEDICINE_DB, n=1, cutoff=0.75)
        if matches:
            return matches[0].capitalize(), True
        return name, False

    # ═══════════════════════════════════════════════════════════════════════════
    #  PDF REPORT GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_pdf_report(self, ocr_result, output_path):
        """Generate a clean PDF report from OCR JSON results."""
        try:
            from fpdf import FPDF
        except ImportError:
            logger.error("fpdf2 not installed — cannot generate PDF")
            return None

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "Medical Prescription Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        # Doctor & Date
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"Doctor: {ocr_result.get('doctor_name', 'Not detected')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Visit Date: {ocr_result.get('visit_date', 'Not detected')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Confidence: {ocr_result.get('confidence', 0)}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Engines Used: {', '.join(ocr_result.get('engines_used', []))}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Diagnoses
        diagnoses = ocr_result.get("diagnoses", [])
        if diagnoses:
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Diagnoses", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for d in diagnoses:
                pdf.cell(0, 7, f"  - {d}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # Medicines Table
        medicines = ocr_result.get("medicines", [])
        if medicines:
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Medications", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            # Table Header
            pdf.set_font("Helvetica", "B", 9)
            col_widths = [50, 25, 30, 30, 25, 20]
            headers = ["Medicine", "Dosage", "Frequency", "Duration", "Route", "Valid"]
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 8, h, border=1, align="C")
            pdf.ln()

            # Table Body
            pdf.set_font("Helvetica", "", 9)
            for med in medicines:
                pdf.cell(col_widths[0], 7, med.get("name", "")[:25], border=1)
                pdf.cell(col_widths[1], 7, med.get("dosage", "")[:12], border=1, align="C")
                pdf.cell(col_widths[2], 7, med.get("frequency", "")[:15], border=1, align="C")
                pdf.cell(col_widths[3], 7, med.get("duration", "")[:15], border=1, align="C")
                pdf.cell(col_widths[4], 7, med.get("route", "")[:12], border=1, align="C")
                pdf.cell(col_widths[5], 7, "Yes" if med.get("validated") else "No", border=1, align="C")
                pdf.ln()
            pdf.ln(5)

        # Raw Text
        raw_text = ocr_result.get("raw_text", "")
        if raw_text:
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Raw Extracted Text", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Courier", "", 8)
            for line in raw_text.split('\n')[:50]:  # Limit to 50 lines
                safe_line = line.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 5, safe_line[:100], new_x="LMARGIN", new_y="NEXT")

        pdf.output(output_path)
        logger.info(f"PDF report saved: {output_path}")
        return output_path

    # ═══════════════════════════════════════════════════════════════════════════
    #  FILE PROCESSING (Image + PDF input)
    # ═══════════════════════════════════════════════════════════════════════════

    def process_file(self, file_path):
        """Process any supported file (image or PDF)."""
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return self._process_pdf(file_path)
        else:
            return self.get_text(file_path)

    def _process_pdf(self, pdf_path):
        """Convert PDF pages to images and run OCR on each."""
        try:
            import pypdfium2 as pdfium
        except ImportError:
            logger.warning("pypdfium2 not installed — trying as image")
            return self.get_text(pdf_path)

        combined_results = {
            "doctor_name": "Not detected",
            "medicines": [],
            "diagnoses": [],
            "raw_text": "",
            "confidence": 0.0,
            "engines_used": [],
            "pages_processed": 0,
        }

        try:
            pdf = pdfium.PdfDocument(pdf_path)
            page_count = len(pdf)
            logger.info(f"Processing PDF: {page_count} page(s)")
            all_confidences = []

            for i in range(min(page_count, 5)):
                page = pdf[i]
                bitmap = page.render(scale=300/72)
                pil_image = bitmap.to_pil()
                temp_img = f"{pdf_path}_page_{i}.png"
                pil_image.save(temp_img)

                page_result = self.get_text(temp_img)

                combined_results["raw_text"] += f"\n--- Page {i+1} ---\n{page_result['raw_text']}"
                if page_result["doctor_name"] != "Not detected":
                    combined_results["doctor_name"] = page_result["doctor_name"]
                for med in page_result["medicines"]:
                    if not any(m['name'].lower() == med['name'].lower() for m in combined_results["medicines"]):
                        combined_results["medicines"].append(med)
                if page_result.get("confidence", 0) > 0:
                    all_confidences.append(page_result["confidence"])
                for eng in page_result.get("engines_used", []):
                    if eng not in combined_results["engines_used"]:
                        combined_results["engines_used"].append(eng)
                for key in ["patient_name", "patient_age", "patient_gender", "visit_date", "diagnoses"]:
                    if key in page_result and key not in combined_results:
                        combined_results[key] = page_result[key]

                if os.path.exists(temp_img):
                    os.remove(temp_img)

            combined_results["pages_processed"] = min(page_count, 5)
            combined_results["confidence"] = round(sum(all_confidences) / len(all_confidences), 1) if all_confidences else 0.0

        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            combined_results["raw_text"] = f"PDF processing error: {str(e)}"

        return combined_results


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════
_tesseract_path = os.environ.get("TESSERACT_PATH")
if not _tesseract_path:
    _default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default):
        _tesseract_path = _default

ocr_service = OcrService(tesseract_path=_tesseract_path)
