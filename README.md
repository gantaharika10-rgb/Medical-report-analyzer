# 🏥 MedScan — Medical Report Analyzer

**100% Local · No API Keys · No Cloud · Works Offline**

Upload any medical report (PDF or image) → extract text with OCR → analyze clinically → summarize in 30+ languages.

---

## What It Does

| Feature | How |
|---|---|
| PDF text extraction | pdfplumber (text layer) |
| Scanned PDF / Image OCR | Tesseract OCR via pytesseract + OpenCV |
| Medical analysis | Rule-based NLP + scikit-learn classifier |
| Vital sign extraction | Regex patterns |
| ICD-10 code hints | Keyword mapping |
| Anomaly detection | Normal range comparison |
| Multi-language summary | deep-translator (no API key) |

---

## Step-by-Step Local Setup

### Step 1 — Install Python

Download Python 3.10+ from https://python.org/downloads

Verify:
```bash
python --version   # should show 3.10+
```

---

### Step 2 — Install Tesseract OCR Engine

Tesseract is the OCR engine used to read text from images and scanned PDFs.

**Windows:**
1. Download installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (default path: `C:\Program Files\Tesseract-OCR\`)
3. Add to PATH: Search "Environment Variables" → Edit PATH → Add `C:\Program Files\Tesseract-OCR`

**macOS:**
```bash
brew install tesseract
```

**Ubuntu / Debian Linux:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr -y
sudo apt-get install poppler-utils -y   # needed for pdf2image
```

**Verify Tesseract:**
```bash
tesseract --version
```

---

### Step 3 — Install Poppler (for PDF→Image conversion)

**Windows:**
1. Download: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to `C:\poppler\`
3. Add `C:\poppler\Library\bin` to PATH

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt-get install poppler-utils -y
```

---

### Step 4 — Download This Project

If you have the zip, extract it. Otherwise clone/copy the folder.

Navigate into the project:
```bash
cd medical-report-analyzer
```

---

### Step 5 — Create Virtual Environment

```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

---

### Step 6 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `flask` — web server
- `pdfplumber` — PDF text extraction
- `pytesseract` — OCR binding
- `opencv-python` — image preprocessing
- `pdf2image` — converts PDF pages to images for OCR
- `deep-translator` — translation (no API key needed)
- `scikit-learn` — ML classifier
- `Pillow` — image handling
- `numpy` — numerical operations

---

### Step 7 — Run the Application

```bash
python app.py
```

You should see:
```
=======================================================
  Medical Report Analyzer  -  100% Local
=======================================================
  No external APIs - Runs offline after setup
  Open: http://localhost:5000
=======================================================
```

---

### Step 8 — Open in Browser

Go to: **http://localhost:5000**

---

## How to Use

1. Click **"Choose File"** or drag & drop a medical report (PDF, JPG, PNG, TIFF, BMP)
2. Select your **summary language** from the dropdown (30+ languages)
3. Click **"Analyze Report"**
4. View:
   - Risk level score
   - Extracted vital signs & lab values
   - Anomaly detection
   - ICD-10 diagnostic code hints
   - Medications detected
   - Clinical section breakdown
   - AI summary in English + your selected language

---

## Kaggle Datasets (Optional — for Training)

Download these CSV files to improve the ML model:

| Dataset | Link | Use |
|---|---|---|
| Medical Transcription Samples | https://www.kaggle.com/datasets/andrewmvd/medical-specialty | **Primary** specialty classifier |
| Medical Notes NLP | https://www.kaggle.com/datasets/tboyle10/medicalnotes | NLP training |
| Pima Diabetes | https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database | Diabetes risk |
| Heart Failure Prediction | https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction | Cardiology risk |
| Chest X-Ray Reports | https://www.kaggle.com/datasets/redwankarimsony/chest-xray-report | Radiology NLP |

**After downloading:**
1. Place CSV files in `data/kaggle_datasets/`
2. Run `python train_model.py`
3. Restart the app

---

## Troubleshooting

**"tesseract not found"**
- Make sure Tesseract is installed and in PATH
- Windows: Restart terminal after adding to PATH
- Test: `tesseract --version`

**"pdf2image error"**
- Install Poppler (see Step 3)
- Windows: Make sure the bin folder is in PATH

**"Translation not working"**
- deep-translator requires internet for translation only
- Everything else works offline
- Install: `pip install deep-translator`

**Port already in use**
```bash
# Change port in app.py last line:
app.run(debug=True, host='0.0.0.0', port=5001)
```

---

## Project Structure

```
medical-report-analyzer/
├── app.py                    ← Flask server
├── requirements.txt          ← All dependencies
├── README.md                 ← This file
├── templates/
│   └── index.html            ← Full UI
├── utils/
│   ├── extractor.py          ← PDF + Image OCR
│   ├── analyzer.py           ← Medical NLP analysis
│   ├── translator.py         ← Multi-language translation
│   └── sample_report.py      ← Built-in demo report
├── models/                   ← Trained ML models saved here
├── uploads/                  ← Temp upload folder (auto-cleaned)
└── data/
    └── kaggle_datasets/      ← Place downloaded CSVs here
```

---

## Disclaimer

> This tool is for **educational and research purposes only**.
> It is NOT a medical device and must NOT be used for clinical decisions.
> Always consult a licensed healthcare professional.
