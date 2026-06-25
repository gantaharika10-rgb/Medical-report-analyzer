"""
Medical Report Preprocessor
Cleans and normalizes medical text for analysis
"""

import re
import string


class ReportPreprocessor:
    """Cleans raw medical report text for analysis"""

    # Common medical abbreviations to expand
    ABBREVIATIONS = {
        r'\bhx\b':    'history',
        r'\bpt\b':    'patient',
        r'\bc/o\b':   'complains of',
        r'\bs/p\b':   'status post',
        r'\br/o\b':   'rule out',
        r'\bdx\b':    'diagnosis',
        r'\btx\b':    'treatment',
        r'\brx\b':    'prescription',
        r'\bpx\b':    'prognosis',
        r'\bsob\b':   'shortness of breath',
        r'\bcp\b':    'chest pain',
        r'\bha\b':    'headache',
        r'\bn/v\b':   'nausea and vomiting',
        r'\bhtm\b':   'hypertension',
        r'\bhtn\b':   'hypertension',
        r'\bdm\b':    'diabetes mellitus',
        r'\bcad\b':   'coronary artery disease',
        r'\bchf\b':   'congestive heart failure',
        r'\baf\b':    'atrial fibrillation',
        r'\bmi\b':    'myocardial infarction',
        r'\bcva\b':   'cerebrovascular accident',
        r'\buti\b':   'urinary tract infection',
        r'\burti\b':  'upper respiratory tract infection',
        r'\bcopd\b':  'copd',
        r'\bgerd\b':  'gastroesophageal reflux disease',
        r'\bpvd\b':   'peripheral vascular disease',
        r'\bbph\b':   'benign prostatic hyperplasia',
        r'\bckd\b':   'chronic kidney disease',
        r'\besrd\b':  'end stage renal disease',
        r'\bniddm\b': 'non-insulin dependent diabetes mellitus',
        r'\biddm\b':  'insulin dependent diabetes mellitus',
        r'\bwbc\b':   'wbc',
        r'\brbc\b':   'rbc',
        r'\bhgb\b':   'hemoglobin',
        r'\bhct\b':   'hematocrit',
        r'\bbun\b':   'bun',
        r'\bcr\b':    'creatinine',
        r'\bbp\b':    'blood pressure',
        r'\bhr\b':    'heart rate',
        r'\brr\b':    'respiratory rate',
        r'\btemp\b':  'temperature',
        r'\bspo2\b':  'spo2',
        r'\bo2sat\b': 'spo2',
    }

    def clean_text(self, text: str) -> str:
        """Full cleaning pipeline"""
        text = self._remove_headers(text)
        text = self._expand_abbreviations(text)
        text = self._normalize_whitespace(text)
        text = self._normalize_units(text)
        return text.strip()

    def _remove_headers(self, text: str) -> str:
        """Remove common report headers/footers"""
        # Remove page numbers
        text = re.sub(r'page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
        # Remove timestamps in headers
        text = re.sub(r'printed?:?\s*\d{1,2}/\d{1,2}/\d{2,4}', '', text, flags=re.IGNORECASE)
        # Remove "CONFIDENTIAL" banners
        text = re.sub(r'\bconfidential\b', '', text, flags=re.IGNORECASE)
        return text

    def _expand_abbreviations(self, text: str) -> str:
        """Expand medical abbreviations"""
        text_lower = text.lower()
        for pattern, expansion in self.ABBREVIATIONS.items():
            text_lower = re.sub(pattern, expansion, text_lower, flags=re.IGNORECASE)
        return text_lower

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace and line breaks"""
        text = re.sub(r'\r\n|\r', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text

    def _normalize_units(self, text: str) -> str:
        """Normalize common unit variations"""
        replacements = [
            (r'mg\s*/\s*dl', 'mg/dl'),
            (r'mmol\s*/\s*l', 'mmol/l'),
            (r'meq\s*/\s*l', 'meq/l'),
            (r'g\s*/\s*dl', 'g/dl'),
            (r'k\s*/\s*ul', 'k/ul'),
            (r'beats?\s*/\s*min', 'bpm'),
            (r'breaths?\s*/\s*min', 'breaths/min'),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
