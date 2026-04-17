# 🩺 Medora: Smart Medical Record System
### *AI-Powered Clinical Intelligence & Prescription Analytics*

Medora is a state-of-the-art health platform designed to transform messy, handwritten medical prescriptions into structured, actionable digital records. Using a robust **Triple-Engine OCR Pipeline** and **Gemini 2.0 Flash**, Medora provides industry-leading accuracy for medical text extraction and historical health intelligence.

---

## 🚀 Key Features

### 1. Unified OCR Excellence
- **Triple-Engine Hybrid Pipeline**: Orchestrates **PaddleOCR v5**, **EasyOCR**, and **Tesseract** for superior local extraction of both printed and handwritten text.
- **Gemini Cloud Rotation**: High-accuracy extraction using Google Gemini 2.0 Flash with automatic model rotation (`2.0 Flash` -> `1.5 Flash` -> `Flash-Lite`) to maximize quota efficiency and prevent downtime.
- **Robust Model Fallback**: Transparently switches to local OCR engines if the Cloud API is unavailable or limits are reached.

### 2. Clinical Intelligence
- **Medication Extraction**: Automatically identifies drugs, dosages, frequencies (e.g., BD, OD, 1-0-1), and durations.
- **Historical Analysis**: Gemini-powered summaries that analyze your entire medical history to find trends, drug interactions, and recovery progress.
- **Auto-Reminders**: Smart scheduling of medication alarms derived directly from scanned data.

### 3. Premium Clinical Experience
- **Modern Dashboard**: High-fidelity dashboard built with **React** and **Lucide React**.
- **Data Visualization**: Health adherence and record growth tracking via **Recharts**.
- **Verification Mode**: Human-in-the-loop review system to verify and edit AI extractions before permanent storage.

---

## 🛠️ Technical Architecture

### **Backend (API Layer)**
- **Framework**: FastAPI (Python)
- **Database**: Neon (Serverless PostgreSQL)
- **ORM**: SQLAlchemy
- **Security**: JWT Authentication (JOSE), Password Hashing (BCRYPT)
- **AI/ML**: google-genai SDK, PaddleOCR, OpenCV

### **Frontend (UI Layer)**
- **Framework**: React 18+ (Vite)
- **Styling**: Vanilla CSS + Bootstrap 5 (Custom Design System)
- **Charts**: Recharts
- **Icons**: Lucide React

---

## 📦 Installation & Setup

### **Prerequisites**
- Python 3.10+
- Node.js 18+
- Tesseract OCR (Optional for local mode)

### **Auto-Launcher (Windows)**
Run the included `start.bat` file. This script will:
1. Activate the Python virtual environment.
2. Launch the FastAPI Uvicorn server (Port 8000).
3. Start the Vite React development server.

### **Manual Backend Setup**
```bash
cd server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Configure .env with your DATABASE_URL and GOOGLE_API_KEY
python init_db.py
uvicorn app.main:app --reload
```

### **Manual Frontend Setup**
```bash
cd client
npm install
npm run dev
```

---

## 🛡️ Security & Privacy
- **Environment Isolation**: Sensitive keys are managed via `.env` and never pushed to version control.
- **No Persistence Fallback**: Local OCR processing ensures data stays on your server if cloud processing is disabled.
- **HIPAA Compliance Patterning**: Designed with data audit logs and encrypted storage paths (AES-256).

---

## 📄 License
This project is for demonstration and research purposes.

---
**Medora | Smarter Health for a Safer World**
