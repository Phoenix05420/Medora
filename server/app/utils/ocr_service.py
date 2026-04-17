"""
Smart Medical OCR Service — Triple-Engine Hybrid Pipeline
Engines: PaddleOCR v5 (primary) + EasyOCR (secondary) + Tesseract (tertiary)
Preprocessing: Adaptive thresholding, CLAHE contrast, auto-deskew, denoising
"""

import os
import cv2
import numpy as np
import logging
import re
import time
from difflib import get_close_matches
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_fixed

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
except ImportError:
    logger.warning("PaddleOCR not installed — skipping engine.")

try:
    import easyocr
    _easyocr_available = True
except ImportError:
    logger.warning("EasyOCR not installed — skipping engine.")

try:
    import pytesseract
    _tesseract_available = True
except ImportError:
    logger.warning("pytesseract not installed — skipping engine.")

try:
    from google import genai
    _gemini_available = True
except ImportError:
    logger.warning("google-genai not installed — skipping Cloud OCR.")
    _gemini_available = False


class OcrService:
    """Triple-engine hybrid OCR with advanced preprocessing and medical parsing."""

    def __init__(self, tesseract_path=None):
        # ── PaddleOCR ──
        self.paddle = None
        if _paddle_available:
            try:
                self.paddle = PaddleOCR(
                    use_textline_orientation=False,
                    enable_mkldnn=False,
                    lang='en'
                )
                logger.info("PaddleOCR v5 initialized (MKLDNN disabled for stability)")
            except Exception as e:
                logger.error(f"PaddleOCR init failed: {e}")

        # ── EasyOCR ──
        self.easy_reader = None
        if _easyocr_available:
            try:
                self.easy_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                logger.info("EasyOCR initialized (CPU mode)")
            except Exception as e:
                logger.error(f"EasyOCR init failed: {e}")

        # ── Tesseract ──
        self.has_tesseract = False
        if _tesseract_available:
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            # Verify tesseract binary is actually installed
            try:
                pytesseract.get_tesseract_version()
                self.has_tesseract = True
                logger.info(f"Tesseract configured (path: {tesseract_path or 'system default'})")
            except Exception:
                logger.warning("pytesseract installed but Tesseract binary not found — skipping engine")

        active = sum([self.paddle is not None, self.easy_reader is not None, self.has_tesseract])
        logger.info(f"Local OCR ready — {active}/3 engines active")

        # ── Gemini (Cloud OCR) ──
        self.gemini_client = None
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        
        # Primary and fallback models for rotation
        self.gemini_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-2.0-flash-lite']
        
        if _gemini_available and self.google_api_key and "YOUR_GEMINI_API_KEY" not in self.google_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.google_api_key)
                logger.info(f"✅ Gemini Cloud OCR initialized (Primary Model: {self.gemini_models[0]})")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")
        else:
            if _gemini_available:
                logger.warning("Gemini API key missing or placeholder in .env — Cloud OCR disabled")
            else:
                logger.warning("google-genai not installed — Cloud OCR disabled")

    # ═══════════════════════════════════════════════════════════════════════════
    #  IMAGE PREPROCESSING PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════

    def preprocess(self, image_path):
        """Full preprocessing pipeline for medical documents."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Step 1: Resize if too large (memory/speed optimization)
        h, w = img.shape[:2]
        max_dim = 2000
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            logger.info(f"Resized from {w}x{h} to {img.shape[1]}x{img.shape[0]}")

        # Step 2: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Step 3: CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # Refined clipLimit for medical labels which often have glare
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Step 4: Denoise (bilateral filter)
        # Slightly stronger denoising for better OCR results
        denoised = cv2.bilateralFilter(enhanced, 11, 85, 85)

        # Step 5: Adaptive thresholding for binarization
        # Use Gaussian method — better for text with varying backgrounds
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11, C=2
        )

        # Step 6: Deskew (straighten rotated scans)
        binary = self._deskew(binary)

        # Step 7: Morphological cleanup — remove tiny noise dots
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        return img, cleaned  # Return both original (for PaddleOCR) and processed

    def _deskew(self, image):
        """Auto-correct document rotation using Hough Line Transform."""
        try:
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                     minLineLength=100, maxLineGap=10)
            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    if abs(angle) < 15:  # Only consider near-horizontal lines
                        angles.append(angle)

                if angles:
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.5:  # Only deskew if meaningful rotation
                        h, w = image.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        image = cv2.warpAffine(image, M, (w, h),
                                                flags=cv2.INTER_CUBIC,
                                                borderMode=cv2.BORDER_REPLICATE)
                        logger.info(f"Deskewed by {median_angle:.1f}°")
        except Exception as e:
            logger.warning(f"Deskew failed (non-critical): {e}")
        return image

    # ═══════════════════════════════════════════════════════════════════════════
    #  TRIPLE-ENGINE OCR
    # ═══════════════════════════════════════════════════════════════════════════

    def get_text(self, image_path):
        """Run all available OCR engines and fuse results."""
        results = {
            "doctor_name": "Not detected",
            "medicines": [],
            "raw_text": "",
            "confidence": 0.0,
            "engines_used": []
        }

        converted_path = None  # Track if we created a converted file

        try:
            # Step 0: Convert unsupported formats (webp, tiff, heic) to PNG
            # PaddleOCR only supports: jpg, png, jpeg, bmp, pdf
            ext = Path(image_path).suffix.lower()
            supported_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.pdf'}
            if ext not in supported_exts:
                logger.info(f"Converting unsupported format '{ext}' to PNG...")
                from PIL import Image
                pil_img = Image.open(image_path)
                converted_path = image_path + "_converted.png"
                pil_img.save(converted_path, "PNG")
                image_path = converted_path
                logger.info(f"Converted successfully: {converted_path}")

            original_img, preprocessed_img = self.preprocess(image_path)

            # Save preprocessed image for engines that need a file path
            prep_path = image_path + "_preprocessed.png"
            cv2.imwrite(prep_path, preprocessed_img)

            # ── Engine 0: Gemini (Cloud OCR - Primary if available) ──
            if self.gemini_client:
                try:
                    gemini_result = self._run_gemini(image_path)
                    if gemini_result:
                        # Success! Gemini handles both extraction and parsing
                        gemini_result["engines_used"] = ["Gemini Cloud AI"]
                        return gemini_result
                except Exception as e:
                    logger.warning(f"Gemini Cloud OCR failed, falling back to local: {e}")

            # ── Engine 1: PaddleOCR (best for printed text & layout) ──
            paddle_lines = self._run_paddle(image_path)

            # ── Engine 2: EasyOCR (best for handwriting & mixed fonts) ──
            easy_lines = self._run_easyocr(prep_path)

            # ── Engine 3: Tesseract (reliable backup) ──
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
            logger.error(f"OCR Pipeline Critical Error: {e}")
            results["raw_text"] = f"Error processing image: {str(e)}"
            # Cleanup on error too
            if converted_path and os.path.exists(converted_path):
                os.remove(converted_path)

        return results

    def _run_paddle(self, image_path):
        """PaddleOCR engine — returns list of (text, confidence) tuples."""
        if not self.paddle:
            return []
        try:
            res = self.paddle.predict(image_path)
            if res and len(res) > 0:
                texts = res[0].get('rec_texts', [])
                scores = res[0].get('rec_scores', [])
                lines = list(zip(texts, scores)) if scores else [(t, 0.9) for t in texts]
                logger.info(f"PaddleOCR: {len(lines)} lines, avg conf {np.mean(scores):.2f}" if scores else f"PaddleOCR: {len(lines)} lines")
                return lines
        except Exception as e:
            logger.error(f"PaddleOCR engine error: {e}")
        return []

    def _run_easyocr(self, image_path):
        """EasyOCR engine — returns list of (text, confidence) tuples."""
        if not self.easy_reader:
            return []
        try:
            results = self.easy_reader.readtext(image_path)
            lines = [(text, conf) for (_, text, conf) in results]
            logger.info(f"EasyOCR: {len(lines)} lines")
            return lines
        except Exception as e:
            logger.error(f"EasyOCR engine error: {e}")
        return []

    def _run_tesseract(self, preprocessed_img):
        """Tesseract engine — returns list of (text, confidence) tuples."""
        if not self.has_tesseract:
            return []
        try:
            # Use OEM 3 (default) + PSM 6 (block of text) for best results
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(preprocessed_img, config=custom_config)
            lines = [(line.strip(), 0.7) for line in text.split('\n') if line.strip()]
            logger.info(f"Tesseract: {len(lines)} lines")
            return lines
        except Exception as e:
            logger.error(f"Tesseract engine error: {e}")
        return []

    def _run_gemini(self, image_path):
        """Gemini engine with robust retries and model rotation fallback."""
        if not self.gemini_client:
            return None

        for model_name in self.gemini_models:
            try:
                return self._attempt_gemini_extraction(image_path, model_name)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logger.warning(f"⚠️ Model {model_name} exhausted (429). Rotating to next model...")
                    time.sleep(1) # Small pause before trying next model
                    continue
                else:
                    logger.error(f"❌ Gemini error ({model_name}): {e}")
                    break
        return None

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(2),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def _attempt_gemini_extraction(self, image_path, model_name):
        """Individual attempt with tenacity retry support."""
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            prompt = """
            Analyze this medical prescription image and extract all relevant information.
            Return the output strictly as a valid JSON object with the following structure:
            {
                "doctor_name": "Doctor Name (use 'Not detected' if missing)",
                "patient_name": "Full Patient Name",
                "patient_age": "Age string",
                "patient_gender": "Male/Female/Other",
                "visit_date": "Date of visit (YYYY-MM-DD or as written)",
                "diagnoses": ["List", "of", "conditions"],
                "medicines": [
                    {
                        "name": "Medicine Name",
                        "dosage": "e.g. 500mg or 1 tab",
                        "frequency": "e.g. 1-0-1 or Twice daily",
                        "duration": "e.g. 5 days",
                        "route": "e.g. oral",
                        "validated": true
                    }
                ],
                "raw_text": "A full dump of all text you see in the image",
                "confidence": 95.0
            }
            Do not include any markdown formatting or tags - just raw JSON.
            Explain: If any medicine name is corrected from clear OCR typos, set 'validated' to true.
            """
            
            response = self.gemini_client.models.generate_content(
                model=model_name,
                contents=[prompt, img]
            )
            text_response = response.text.strip()
            
            # Clean up potential markdown formatting
            if text_response.startswith("```"):
                text_response = re.sub(r"```json\s?|\s?```", "", text_response)
            
            import json
            result = json.loads(text_response)
            logger.info(f"✅ Gemini Cloud OCR ({model_name}) successful")
            return result
        except Exception as e:
            # Re-raise so tenacity/rotation can handle
            raise e

    def _fuse_results(self, paddle_lines, easy_lines, tess_lines):
        """
        Intelligent multi-engine text fusion.
        Strategy: Prioritize by confidence, deduplicate similar lines.
        """
        # Combine all lines with their source confidence
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
                    # Keep the higher-confidence version
                    if conf > existing_conf:
                        unique_lines[i] = (text, conf, src)
                    break
            if not is_duplicate:
                unique_lines.append((text, conf, src))

        # Sort by confidence descending, then join
        # But preserve reading order — group by source that has best overall confidence
        best_source_lines = sorted(unique_lines, key=lambda x: -x[1])
        return "\n".join([line[0] for line in best_source_lines])

    @staticmethod
    def _text_similarity(a, b):
        """Simple character-level Jaccard similarity."""
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
    #  MEDICAL DATA EXTRACTION (v3 — fuzzy matching + expanded DB)
    # ═══════════════════════════════════════════════════════════════════════════

    # 300+ common medicine names for validation + fuzzy correction
    MEDICINE_DB = {
        # ── Cardiovascular ──
        "amlodipine", "atenolol", "bisoprolol", "carvedilol", "diltiazem",
        "enalapril", "lisinopril", "losartan", "metoprolol", "nifedipine",
        "propranolol", "ramipril", "telmisartan", "valsartan", "verapamil",
        "clopidogrel", "warfarin", "rivaroxaban", "apixaban", "dabigatran",
        "aspirin", "ticagrelor", "prasugrel", "enoxaparin", "heparin",
        "furosemide", "hydrochlorothiazide", "spironolactone", "torsemide",
        "indapamide", "digoxin", "amiodarone", "nitroglycerine", "isosorbide",
        # ── Diabetes ──
        "metformin", "glimepiride", "gliclazide", "glipizide", "sitagliptin",
        "vildagliptin", "linagliptin", "saxagliptin", "empagliflozin",
        "dapagliflozin", "canagliflozin", "pioglitazone", "acarbose",
        "insulin", "liraglutide", "semaglutide", "dulaglutide",
        # ── Cholesterol / Lipids ──
        "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
        "lovastatin", "fenofibrate", "ezetimibe", "gemfibrozil",
        # ── Gastrointestinal ──
        "omeprazole", "pantoprazole", "esomeprazole", "lansoprazole",
        "rabeprazole", "ranitidine", "famotidine", "sucralfate",
        "domperidone", "metoclopramide", "ondansetron", "loperamide",
        "bisacodyl", "lactulose", "mesalamine", "sulfasalazine",
        # ── Pain / Anti-inflammatory ──
        "paracetamol", "acetaminophen", "ibuprofen", "diclofenac",
        "naproxen", "celecoxib", "etoricoxib", "indomethacin",
        "piroxicam", "meloxicam", "ketorolac", "tramadol",
        "morphine", "fentanyl", "oxycodone", "codeine", "tapentadol",
        "pregabalin", "gabapentin", "duloxetine", "amitriptyline",
        # ── Antibiotics ──
        "amoxicillin", "ampicillin", "penicillin", "cloxacillin",
        "azithromycin", "erythromycin", "clarithromycin", "roxithromycin",
        "ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin",
        "doxycycline", "tetracycline", "minocycline",
        "cephalexin", "cefuroxime", "cefixime", "ceftriaxone", "cefpodoxime",
        "meropenem", "imipenem", "piperacillin", "vancomycin",
        "clindamycin", "metronidazole", "linezolid", "nitrofurantoin",
        "trimethoprim", "sulfamethoxazole", "gentamicin", "amikacin",
        "colistin", "rifampicin", "isoniazid", "pyrazinamide", "ethambutol",
        # ── Antifungal / Antiviral ──
        "fluconazole", "itraconazole", "voriconazole", "amphotericin",
        "clotrimazole", "terbinafine", "nystatin",
        "acyclovir", "valacyclovir", "oseltamivir", "tenofovir",
        "lamivudine", "efavirenz", "lopinavir", "ritonavir", "remdesivir",
        # ── Respiratory ──
        "salbutamol", "albuterol", "ipratropium", "tiotropium",
        "budesonide", "fluticasone", "beclomethasone", "formoterol",
        "salmeterol", "montelukast", "theophylline", "aminophylline",
        "dextromethorphan", "guaifenesin", "bromhexine", "ambroxol",
        "cetirizine", "levocetirizine", "loratadine", "fexofenadine",
        "chlorpheniramine", "diphenhydramine", "hydroxyzine",
        # ── Steroids / Immunology ──
        "prednisone", "prednisolone", "methylprednisolone", "dexamethasone",
        "hydrocortisone", "betamethasone", "triamcinolone", "deflazacort",
        "azathioprine", "mycophenolate", "tacrolimus", "cyclosporine",
        # ── Psychiatry / Neurology ──
        "sertraline", "escitalopram", "fluoxetine", "paroxetine", "citalopram",
        "venlafaxine", "desvenlafaxine", "mirtazapine", "bupropion",
        "alprazolam", "diazepam", "lorazepam", "clonazepam", "midazolam",
        "olanzapine", "quetiapine", "risperidone", "aripiprazole", "haloperidol",
        "lithium", "valproate", "carbamazepine", "lamotrigine", "topiramate",
        "levetiracetam", "phenytoin", "phenobarbital", "oxcarbazepine",
        "donepezil", "memantine", "levodopa", "carbidopa", "ropinirole",
        "pramipexole", "trihexyphenidyl", "baclofen", "tizanidine",
        "zolpidem", "zopiclone", "melatonin",
        # ── Endocrine / Thyroid ──
        "levothyroxine", "methimazole", "propylthiouracil",
        "testosterone", "estradiol", "progesterone", "tamoxifen",
        "letrozole", "anastrozole", "finasteride", "dutasteride",
        # ── Vitamins / Supplements ──
        "multivitamin", "calcium", "vitamin", "folic", "ferrous",
        "iron", "zinc", "magnesium", "potassium", "cholecalciferol",
        "cyanocobalamin", "pyridoxine", "thiamine", "riboflavin",
        # ── Eye / ENT ──
        "timolol", "latanoprost", "brimonidine", "dorzolamide",
        "ciprofloxacin", "tobramycin", "moxifloxacin",
        # ── Miscellaneous ──
        "sildenafil", "tadalafil", "tamsulosin", "alfuzosin",
        "allopurinol", "colchicine", "febuxostat",
        "hydroxychloroquine", "methotrexate", "leflunomide",
    }

    def _parse_medical_data(self, text, results):
        """Extract structured medical data from raw OCR text (v3)."""

        # ── Doctor Name ──
        doc_patterns = [
            r"(?:Dr\.|Doctor|Physician)\.?\s+([A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2})",
            r"(?:Doctor|Consultant|Prescribed\s+by):?\s+([A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2})",
            r"(?:Attending|Surgeon|Specialist):?\s+(?:Dr\.?\s+)?([A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2})",
        ]
        for p in doc_patterns:
            match = re.search(p, text, re.I)
            if match:
                results["doctor_name"] = match.group(1).strip()
                break

        # ── Patient Info ──
        patient_patterns = [
            r"(?:Patient|Name|Pt):?[ \t]+(?:Mr\.?|Mrs\.?|Ms\.?|Miss)?[ \t]*([A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2})",
        ]
        for p in patient_patterns:
            match = re.search(p, text, re.I)
            if match:
                results["patient_name"] = match.group(1).strip()
                break

        age_match = re.search(r"(?:Age|Aged?):?\s*(\d{1,3})\s*(?:y(?:ears?|rs?)?|/)", text, re.I)
        if age_match:
            results["patient_age"] = age_match.group(1)

        gender_match = re.search(r"(?:Sex|Gender):?\s*(Male|Female|M|F)\b", text, re.I)
        if gender_match:
            results["patient_gender"] = gender_match.group(1).strip()

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

        # ── Diagnosis / Condition ──
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
                    # Fuzzy spell correction
                    corrected_name, is_validated = self._fuzzy_match_medicine(med_name)

                    post_text = line_clean[dosage_match.end():].strip()
                    freq_match = re.search(frequency_regex, post_text, re.I)
                    dur_match = re.search(duration_regex, post_text, re.I)
                    route_match = re.search(route_regex, line_clean, re.I)

                    med_entry = {
                        "name": corrected_name,
                        "original_ocr": med_name if corrected_name != med_name else None,
                        "dosage": dosage_match.group(1).strip(),
                        "frequency": freq_match.group(1).strip() if freq_match else "As directed",
                        "duration": dur_match.group(1).strip() if dur_match else "Not specified",
                        "route": route_match.group(1).strip() if route_match else "",
                        "validated": is_validated,
                    }

                    if not any(m['name'].lower() == corrected_name.lower() for m in results["medicines"]):
                        results["medicines"].append(med_entry)
                    continue

            # Strategy 2: Known medicine name lookup (with fuzzy)
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
                        "original_ocr": clean_word if corrected != clean_word else None,
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
        """
        Attempt to match a medicine name against the database.
        Uses exact match first, then fuzzy matching for OCR typos.
        Returns (corrected_name, is_validated).
        """
        lower = name.lower().strip()

        # Exact match
        if lower in self.MEDICINE_DB:
            return name.capitalize(), True

        # Check first word (for multi-word names like "Amlodipine Besylate")
        first_word = lower.split()[0] if lower.split() else lower
        if first_word in self.MEDICINE_DB:
            return first_word.capitalize(), True

        # Fuzzy match — find closest medicine name within edit distance
        # cutoff=0.75 means 75% similarity required
        matches = get_close_matches(lower, self.MEDICINE_DB, n=1, cutoff=0.75)
        if matches:
            logger.info(f"Fuzzy corrected: '{name}' -> '{matches[0].capitalize()}'")
            return matches[0].capitalize(), True

        # No match found — return original
        return name, False

    # ═══════════════════════════════════════════════════════════════════════════
    #  PDF SUPPORT
    # ═══════════════════════════════════════════════════════════════════════════

    def process_file(self, file_path):
        """
        Process any supported file (image or PDF).
        For PDFs, converts each page to an image and runs OCR on all pages.
        """
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
            logger.warning("pypdfium2 not installed — cannot process PDFs")
            return self.get_text(pdf_path)  # fallback: try as image

        combined_results = {
            "doctor_name": "Not detected",
            "medicines": [],
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

            for i in range(min(page_count, 5)):  # Max 5 pages
                page = pdf[i]
                # Render at 300 DPI for good OCR quality
                bitmap = page.render(scale=300/72)
                pil_image = bitmap.to_pil()

                # Save as temp image
                temp_img = f"{pdf_path}_page_{i}.png"
                pil_image.save(temp_img)

                page_result = self.get_text(temp_img)

                # Merge results
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

                # Copy additional fields
                for key in ["patient_name", "patient_age", "patient_gender", "visit_date", "diagnoses"]:
                    if key in page_result and key not in combined_results:
                        combined_results[key] = page_result[key]

                # Cleanup
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
# Auto-detect Tesseract path on Windows
_tesseract_path = os.environ.get("TESSERACT_PATH")
if not _tesseract_path:
    _default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default):
        _tesseract_path = _default

ocr_service = OcrService(tesseract_path=_tesseract_path)

