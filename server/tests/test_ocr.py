"""Test the improved OCR medical parsing logic (v3)."""
import sys, os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.ocr_service import OcrService

def test_parsing():
    service = OcrService()
    
    test_cases = [
        {
            "name": "Standard Prescription",
            "text": "Dr. John Doe\nConsultant Physician\nDate: 15/04/2026\nAmlodipine 5mg 1-0-1 for 30 days oral\nMetformin 500mg BD for 2 weeks",
            "checks": {
                "doctor": "John Doe",
                "meds_count": 2,
                "first_med": "Amlodipine",
                "first_dosage": "5mg",
            }
        },
        {
            "name": "Fuzzy Spell Correction (OCR typos)",
            "text": "Dr. Sarah Miller\nAmlodipiine 5mg OD\nMetformn 500mg BD\nParacetmol 650mg SOS",
            "checks": {
                "doctor": "Sarah Miller",
                "meds_count": 3,
                "first_med_validated": True,
            }
        },
        {
            "name": "Patient Info + Diagnosis Extraction",
            "text": "Patient: Mr. Ramesh Kumar\nAge: 45 years  Sex: Male\nDr. Priya Sharma\nDiagnosis: Type 2 Diabetes Mellitus\nC/O: Frequent urination\nMetformin 500mg BD for 30 days\nGlimepiride 2mg OD morning",
            "checks": {
                "doctor": "Priya Sharma",
                "patient_name": "Ramesh Kumar",
                "patient_age": "45",
                "has_diagnoses": True,
                "meds_count": 2,
            }
        },
        {
            "name": "Complex Prescription with Routes",
            "text": "Doctor: Rajesh Kumar\nDate: 10/04/2026\n1. Ceftriaxone 1g IV BD for 5 days\n2. Pantoprazole 40mg oral OD for 14 days\n3. Insulin 10 units SC TID",
            "checks": {
                "doctor": "Rajesh Kumar",
                "meds_count": 3,
            }
        },
        {
            "name": "Known Medicine Lookup (no dosage)",
            "text": "Dr. Wilson\nTab paracetamol as needed\nomeprazole before meals",
            "checks": {
                "doctor": "Wilson",
                "meds_count": 2,
            }
        },
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {case['name']}")
        print(f"{'='*60}")
        
        results = {
            "doctor_name": "Not detected",
            "medicines": [],
            "raw_text": case["text"],
            "confidence": 0.0,
            "engines_used": []
        }
        service._parse_medical_data(case["text"], results)

        checks = case["checks"]
        errors = []

        if "doctor" in checks and results["doctor_name"] != checks["doctor"]:
            errors.append(f"Doctor: expected '{checks['doctor']}', got '{results['doctor_name']}'")

        if "patient_name" in checks and results.get("patient_name") != checks["patient_name"]:
            errors.append(f"Patient: expected '{checks['patient_name']}', got '{results.get('patient_name', 'None')}'")

        if "patient_age" in checks and results.get("patient_age") != checks["patient_age"]:
            errors.append(f"Age: expected '{checks['patient_age']}', got '{results.get('patient_age', 'None')}'")

        if "has_diagnoses" in checks and checks["has_diagnoses"] and not results.get("diagnoses"):
            errors.append(f"Diagnoses: expected some, got none")

        if "meds_count" in checks and len(results["medicines"]) != checks["meds_count"]:
            errors.append(f"Med count: expected {checks['meds_count']}, got {len(results['medicines'])}")

        if "first_med" in checks and results["medicines"]:
            if results["medicines"][0]["name"] != checks["first_med"]:
                errors.append(f"First med: expected '{checks['first_med']}', got '{results['medicines'][0]['name']}'")

        if "first_med_validated" in checks and results["medicines"]:
            if results["medicines"][0].get("validated") != checks["first_med_validated"]:
                errors.append(f"First med validated: expected {checks['first_med_validated']}")

        # Print results
        print(f"  Doctor: {results['doctor_name']}")
        if results.get("patient_name"):
            print(f"  Patient: {results['patient_name']} (Age: {results.get('patient_age', '?')}, {results.get('patient_gender', '?')})")
        if results.get("diagnoses"):
            print(f"  Diagnoses: {', '.join(results['diagnoses'])}")
        for med in results["medicines"]:
            validated = "OK" if med.get("validated") else "??"
            corrected = f" [corrected from: {med['original_ocr']}]" if med.get("original_ocr") else ""
            print(f"  [{validated}] {med['name']}{corrected} | {med['dosage']} | {med['frequency']} | {med['duration']} | {med.get('route', '')}")

        if errors:
            failed += 1
            for e in errors:
                print(f"  >> FAIL: {e}")
        else:
            passed += 1
            print(f"  >> PASSED")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)}")
    print(f"{'='*60}")
    return failed == 0

if __name__ == "__main__":
    success = test_parsing()
    sys.exit(0 if success else 1)
