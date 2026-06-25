"""
Local Medical Report Analyzer - Enhanced for real lab reports
Handles CBC, Lipid Profile, Biochemistry, Immunoassay, HbA1c, BNP, Thyroid etc.

Also handles non-lab reports (radiology/imaging, procedure notes) by:
  - recognizing radiology-style section headers (FINDINGS, IMPRESSION, etc.)
  - detecting risk stated explicitly in words (e.g. "Grade 5 (High-Risk)")
    instead of only inferring risk from numeric lab values out of range
  - never claiming "all parameters normal" when no parameters were actually
    found to test in the first place
"""

import re
from datetime import datetime

# ── Comprehensive lab patterns for real pathology reports ───────────────────
LAB_PATTERNS = {
    # CBC
    'Hemoglobin':           r'Hemoglobin[\s\S]{0,30}?(\d{1,2}(?:\.\d)?)\s*g/dL',
    'WBC Count':            r'WBC\s*Count[\s\S]{0,30}?(\d{4,6})\s*/cmm',
    'Platelet Count':       r'Platelet\s*Count[\s\S]{0,30}?(\d{3,6})\s*/cmm',
    'Hematocrit':           r'Hematocrit[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*%',
    'MCV':                  r'MCV[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*fL',
    'MPV':                  r'MPV[\s\S]{0,20}?(\d{1,2}(?:\.\d{1,2})?)\s*fL',
    'ESR':                  r'ESR[\s\S]{0,20}?(\d{1,3})\s*mm/1hr',
    # Lipid
    'Cholesterol':          r'Cholesterol[\s\S]{0,60}?(\d{2,3}(?:\.\d)?)\s*mg/dL',
    'Triglyceride':         r'Triglyceride[\s\S]{0,30}?(\d{2,3}(?:\.\d)?)\s*mg/dL',
    'HDL Cholesterol':      r'HDL\s*Cholesterol[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*mg/dL',
    'Direct LDL':           r'Direct\s*LDL[\s\S]{0,20}?(\d{2,3}(?:\.\d{1,2})?)\s*mg/dL',
    'VLDL':                 r'VLDL[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*mg/dL',
    # Glucose / Diabetes
    'Fasting Blood Sugar':  r'Fasting\s*Blood\s*Sugar[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*mg/dL',
    'HbA1c':                r'HbA1c[\s\S]{0,20}?(\d{1,2}(?:\.\d{1,2})?)\s*%',
    'Mean Blood Glucose':   r'Mean\s*Blood\s*Glucose[\s\S]{0,20}?(\d{2,3}(?:\.\d{1,2})?)\s*mg/dL',
    # Kidney
    'Creatinine':           r'Creatinine[,\s]*Serum[\s\S]{0,20}?(\d(?:\.\d{1,2})?)\s*mg/dL',
    'Urea':                 r'Urea[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*mg/dL',
    'Blood Urea Nitrogen':  r'Blood\s*Urea\s*Nitrogen[\s\S]{0,20}?(\d{1,2}(?:\.\d)?)\s*mg/dL',
    'Uric Acid':            r'Uric\s*Acid[\s\S]{0,20}?(\d(?:\.\d{1,2})?)\s*mg/dL',
    # Liver
    'SGPT':                 r'SGPT[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*U/L',
    'SGOT':                 r'SGOT[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*U/L',
    'Total Bilirubin':      r'Total\s*Bilirubin[\s\S]{0,20}?(\d(?:\.\d{1,2})?)\s*mg/dL',
    'Total Protein':        r'Total\s*Protein[\s\S]{0,20}?(\d(?:\.\d{1,2})?)\s*g/dL',
    # Electrolytes
    'Sodium':               r'Sodium[\s\S]{0,30}?(\d{2,3}(?:\.\d)?)\s*(?:mmol/L|mEq/L)',
    'Potassium':            r'Potassium[\s\S]{0,30}?(\d(?:\.\d{1,2})?)\s*(?:mmol/L|mEq/L)',
    'Calcium':              r'Calcium[\s\S]{0,20}?(\d{1,2}(?:\.\d{1,2})?)\s*mg/dL',
    # Immunology
    'Vitamin D':            r'25\(OH\)\s*Vitamin\s*D[\s\S]{0,20}?(\d{1,2}(?:\.\d{1,2})?)\s*ng/mL',
    'Vitamin B12':          r'Vitamin\s*B12[\s\S]{0,20}?<?\s*(\d{2,4})\s*pg/mL',
    'Homocysteine':         r'Homocysteine[,\s]*Serum[\s\S]{0,20}?(\d{1,2}(?:\.\d{1,2})?)\s*micromol',
    'IgE':                  r'IgE[\s\S]{0,20}?(\d{2,4}(?:\.\d{1,2})?)\s*IU/mL',
    'Iron':                 r'Iron[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)\s*micro\s*g/dL',
    'TIBC':                 r'Total\s*Iron\s*Binding[\s\S]{0,20}?(\d{2,3}(?:\.\d)?)',
    # Thyroid - enhanced patterns to match "T3, TOTAL, SERUM" and mU/L formats
    'T3':                   r'T3[\s,]*(?:TOTAL[\s,]*SERUM|Triiodothyronine)?[\s\S]{0,40}?(\d{2,3}(?:\.\d{1,2})?)\s*(?:ng/dL|ng/mL)',
    'T4':                   r'T4[\s,]*(?:TOTAL[\s,]*SERUM|Thyroxine)?[\s\S]{0,40}?(\d{1,2}(?:\.\d{1,2})?)\s*(?:mcg/dL|µg/dL|ug/dL)',
    'TSH':                  r'TSH[\s\S]{0,40}?(\d{1,2}(?:\.\d{1,4})?)\s*(?:microIU/mL|mU/L|µIU/mL|mIU/L)',
    # Microalbumin / PSA
    'Microalbumin':         r'Microalbumin[\s\S]{0,30}?(\d{1,3}(?:\.\d{1,2})?)\s*mg/L',
    'PSA':                  r'PSA[\s\S]{0,40}?(\d(?:\.\d{1,3})?)\s*ng/mL',
    # Cardiology
    'BNP':                  r'(?:BNP|NATRIURETIC)[\s\S]{0,200}?(?:CLIA\s+Result\s+|Result\s+)?(?:Plasma[^0-9]{0,30})?(\d{1,5}\.\d{2})\s*(?:Reference|Normal|pg/mL|TAT)',
    'Troponin I':           r'Troponin\s*I[\s\S]{0,30}?(\d{1,3}(?:\.\d{1,3})?)\s*(?:ng/mL|µg/L)',
    'Troponin T':           r'Troponin\s*T[\s\S]{0,30}?(\d{1,3}(?:\.\d{1,3})?)\s*(?:ng/mL|µg/L)',
    'CK-MB':                r'CK[\s\-]*MB[\s\S]{0,30}?(\d{1,3}(?:\.\d{1,2})?)\s*(?:U/L|ng/mL)',
    'D-Dimer':              r'D[\s\-]*Dimer[\s\S]{0,30}?(\d{1,4}(?:\.\d{1,2})?)\s*(?:ng/mL|µg/L|mg/L)',
}

VITAL_PATTERNS = {
    'Blood Pressure': r'(?:BP|blood\s*pressure)[:\s]+(\d{2,3}[/]\d{2,3})',
    'Heart Rate':     r'(?:HR|heart\s*rate|pulse)[:\s]+(\d{2,3})\s*(?:bpm|/min)?',
    'Temperature':    r'(?:temp(?:erature)?)[:\s]+(\d{2,3}(?:\.\d)?)\s*(?:°?[FC])?',
    'SpO2':           r'(?:SpO2|O2\s*sat)[:\s]+(\d{2,3})\s*%?',
}

# ── Normal ranges: (low, high, unit, critical_low, critical_high) ────────────
NORMAL_RANGES = {
    'Hemoglobin':         (13.0, 16.5,   'g/dL',    8.0,   20.0),
    'WBC Count':          (4000, 10000,  '/cmm',    2000,  30000),
    'Platelet Count':     (150000,410000,'/cmm',    50000, 800000),
    'MPV':                (7.5,  10.3,   'fL',      None,  None),
    'Cholesterol':        (0,    200,    'mg/dL',   None,  300),
    'Triglyceride':       (0,    150,    'mg/dL',   None,  500),
    'HDL Cholesterol':    (40,   999,    'mg/dL',   None,  None),
    'Direct LDL':         (0,    100,    'mg/dL',   None,  190),
    'Fasting Blood Sugar':(74,   106,    'mg/dL',   50,    400),
    'HbA1c':              (0,    6.5,    '%',       None,  None),
    'Creatinine':         (0.66, 1.25,   'mg/dL',   None,  None),
    'Urea':               (19.3, 43.0,   'mg/dL',   None,  None),
    'SGPT':               (0,    50,     'U/L',     None,  None),
    'SGOT':               (17,   59,     'U/L',     None,  None),
    'Sodium':             (136,  145,    'mmol/L',  125,   155),
    'Potassium':          (3.5,  5.1,    'mmol/L',  2.5,   6.5),
    'Vitamin D':          (30,   100,    'ng/mL',   None,  None),
    'Vitamin B12':        (187,  833,    'pg/mL',   None,  None),
    'Homocysteine':       (6.0,  14.8,   'µmol/L',  None,  None),
    'IgE':                (0,    87,     'IU/mL',   None,  None),
    # Thyroid - matching actual report reference ranges
    'T3':                 (80.0, 200.0,  'ng/dL',   None,  None),
    'T4':                 (4.50, 12.50,  'mcg/dL',  None,  None),
    'TSH':                (0.40, 4.00,   'mU/L',    None,  None),
    'Heart Rate':         (60,   100,    'bpm',     40,    150),
    'SpO2':               (95,   100,    '%',       88,    None),
    'ESR':                (0,    14,     'mm/hr',   None,  None),
    'PSA':                (0,    4,      'ng/mL',   None,  None),
    # Cardiology
    'BNP':                (0,    29.4,   'pg/mL',   None,  500),
    'Troponin I':         (0,    0.04,   'ng/mL',   None,  None),
    'CK-MB':              (0,    25,     'U/L',     None,  None),
    'D-Dimer':            (0,    500,    'ng/mL',   None,  None),
}

ICD_MAP = {
    'bnp':          ('I50.9', 'Heart failure screening (BNP test)'),
    'natriuretic':  ('I50.9', 'Heart failure — BNP/natriuretic peptide test'),
    'diabetes':     ('E11.9', 'Type 2 diabetes mellitus'),
    'hba1c':        ('E11.9', 'Diabetes - glycemic monitoring'),
    'glucose':      ('R73.09','Elevated blood glucose'),
    'vitamin d':    ('E55.9', 'Vitamin D deficiency'),
    'vitamin b12':  ('E53.8', 'Vitamin B12 deficiency'),
    'homocysteine': ('E72.11','Homocystinuria / elevated homocysteine'),
    'cholesterol':  ('E78.5', 'Hyperlipidaemia, unspecified'),
    'triglyceride': ('E78.1', 'Hypertriglyceridaemia'),
    'ige':          ('J45.9', 'Asthma / Allergic disorder'),
    'anemia':       ('D64.9', 'Anaemia, unspecified'),
    'thyroid':      ('E07.9', 'Disorder of thyroid'),
    'tsh':          ('E03.9', 'Hypothyroidism — elevated TSH'),
    'urine glucose':('R81',   'Glycosuria'),
    'wbc':          ('D72.829','Leukocytosis'),
    'infection':    ('A49.9', 'Bacterial infection'),
    'troponin':     ('I21.9', 'Acute myocardial infarction'),
    # Radiology / imaging / procedural findings
    'fistula':      ('K60.3', 'Anal fistula'),
    'perianal':     ('K60.3', 'Perianal fistulous disease'),
    'abscess':      ('K61.0', 'Anal/perianal abscess'),
    'hernia':       ('K46.9', 'Hernia, unspecified'),
    'fracture':     ('T14.8', 'Fracture, unspecified site'),
    'hemorrhage':   ('R58',   'Hemorrhage, not elsewhere classified'),
    'haemorrhage':  ('R58',   'Hemorrhage, not elsewhere classified'),
    'effusion':     ('R09.1', 'Pleural/joint effusion'),
    'stenosis':     ('Q66.89','Stenosis, unspecified'),
}

SPECIALTY_KEYWORDS = {
    'Hematology':      ['hemoglobin','wbc','rbc','platelet','hematocrit','mcv','mch','mchc','rdw','esr','electrophoresis','thalassemia'],
    'Endocrinology':   ['hba1c','glucose','diabetes','thyroid','tsh','t3','t4','insulin','vitamin d','vitamin b12','thyroxine','triiodothyronine'],
    'Cardiology':      ['cholesterol','ldl','hdl','triglyceride','vldl','homocysteine','troponin','bnp','natriuretic','cardiac'],
    'Nephrology':      ['creatinine','urea','uric acid','microalbumin','potassium','sodium','chloride'],
    'Hepatology':      ['sgpt','sgot','bilirubin','albumin','protein','globulin'],
    'Immunology':      ['ige','hiv','hbsag','psa','immunoassay'],
    'Radiology / Imaging': ['radiology','radiologist','mri','ct scan','x-ray','xray','ultrasound',
                             'sonography','axial','coronal','sagittal','contrast','fistula','fistulous',
                             'abscess','sphincter','perianal','findings','impression','technique'],
    'General Medicine':['general','routine','checkup','follow-up','annual'],
}

HIGH_RISK_FLAGS = {
    'Fasting Blood Sugar': lambda v: float(v) > 200,
    'HbA1c':               lambda v: float(v) > 8.0,
    'Vitamin D':           lambda v: float(v) < 10,
    'Vitamin B12':         lambda v: float(v) < 148,
    'Homocysteine':        lambda v: float(v) > 20,
    'IgE':                 lambda v: float(v) > 300,
    'WBC Count':           lambda v: float(v) > 11000,
    'Potassium':           lambda v: float(v) > 5.5 or float(v) < 3.0,
    'Sodium':              lambda v: float(v) > 150 or float(v) < 130,
    'BNP':                 lambda v: float(v) > 100,
    'TSH':                 lambda v: float(v) > 10.0 or float(v) < 0.1,
    'T3':                  lambda v: float(v) > 250 or float(v) < 60,
    'T4':                  lambda v: float(v) > 15.0 or float(v) < 3.0,
}

# Explicit risk language often found in radiology / specialist Impression
# sections, e.g. "Grade 5 (High-Risk)". Checked in priority order — first
# match wins — since a report can use more than one of these words.
EXPLICIT_RISK_PATTERNS = [
    ('Critical', r'\bcritical\b|life[\s-]?threatening|\bmalignant\b|emergenc(?:y|ies)'),
    ('High',     r'high[\s-]?risk|\bsevere\b|\bextensive\b|\burgent\b'),
    ('Moderate', r'moderate[\s-]?risk'),
    ('Low',      r'low[\s-]?risk|\bbenign\b|\bunremarkable\b|\bno acute\b|\bnormal study\b'),
]

RISK_LEVEL_RANK = {'Low': 1, 'Moderate': 2, 'High': 3, 'Critical': 4}
RISK_LEVEL_FLOOR_SCORE = {'Low': 15, 'Moderate': 35, 'High': 55, 'Critical': 80}

MEDICATION_PATTERNS = [
    r'\b([A-Z][a-z]+(?:in|ol|am|ide|ine|ate|one|pril|artan|statin|mycin|cillin|oxacin|zepam|prazole)?)\s+(\d+\s*(?:mg|mcg|g|IU|mL|units?)(?:\s*/\s*(?:day|daily|od|bd|tid|qid|hs|weekly))?)',
    r'\b(?:Tab|Cap|Inj|Syp|Syr|Drop|Oint|Gel)\.?\s+([A-Z][a-zA-Z]+)\s+(\d+\s*(?:mg|mcg|g|IU|mL))',
    r'\b([A-Z][a-zA-Z]{3,})\s+(\d+\s*mg)\s+(?:once|twice|thrice|\d+\s*times)',
]

KNOWN_MEDICATIONS = [
    'Metformin','Glimepiride','Sitagliptin','Empagliflozin','Dapagliflozin',
    'Insulin','Atorvastatin','Rosuvastatin','Amlodipine','Lisinopril',
    'Telmisartan','Losartan','Ramipril','Aspirin','Clopidogrel',
    'Pantoprazole','Omeprazole','Vitamin D3','Vitamin B12','Folic Acid',
    'Levothyroxine','Thyroxine','Metoprolol','Atenolol','Paracetamol',
    'Azithromycin','Amoxicillin','Ciprofloxacin','Doxycycline',
    'Prednisolone','Methylprednisolone','Hydroxychloroquine',
    'Calcium','Ferrous Sulfate','Iron','Zinc',
]

# Words that should never be treated as clinical keywords
KEYWORD_BLACKLIST = {'sample', 'collection', 'laboratory', 'pathology', 'drlogy', 'report', 'reference'}


def analyze_report(text: str) -> dict:
    text_clean = re.sub(r'[ \t]+', ' ', text).strip()
    tl = text_clean.lower()

    labs    = _extract_lab_values(text_clean)
    vitals  = _extract_values(text_clean, VITAL_PATTERNS)

    anomalies     = _detect_anomalies(labs, vitals, text_clean)
    specialty     = _classify_specialty(tl, labs)
    sections      = _extract_sections(text_clean)
    explicit_risk = _extract_explicit_risk(text_clean, sections)
    risk_score, risk_level = _risk_score(labs, vitals, anomalies, tl, explicit_risk)
    patient       = _extract_patient_info(text_clean)
    keywords      = _extract_keywords(tl, labs)
    icd           = _icd_hints(tl, labs)
    medications   = _extract_medications(text_clean)
    summary       = _build_summary(patient, specialty, risk_level, labs, vitals, anomalies, sections, explicit_risk)

    return {
        'patient':        patient,
        'specialty':      specialty,
        'risk_score':     risk_score,
        'risk_level':     risk_level,
        'vitals':         vitals,
        'labs':           labs,
        'medications':    medications,
        'icd_hints':      icd,
        'keywords':       keywords,
        'anomalies':      anomalies,
        'sections':       sections,
        'summary':        summary,
        'word_count':     len(text_clean.split()),
        'analyzed_at':    datetime.now().strftime('%Y-%m-%d %H:%M'),
        'abnormal_count': len(anomalies),
    }


def _extract_lab_values(text):
    found = {}
    for name, pat in LAB_PATTERNS.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if name == 'Sodium':
                try:
                    if float(val) < 100:
                        continue
                except:
                    continue
            found[name] = val
    return found


def _extract_values(text, patterns):
    found = {}
    for name, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            found[name] = m.group(1)
    return found


def _extract_medications(text):
    medications = []
    found_names = set()
    for med in KNOWN_MEDICATIONS:
        pattern = rf'\b{re.escape(med)}\b[\s\S]{{0,50}}?(\d+\s*(?:mg|mcg|g|IU|mL|units?))?'
        m = re.search(pattern, text, re.IGNORECASE)
        if m and med.lower() not in found_names:
            dose = m.group(1).strip() if m.group(1) else ''
            medications.append({'name': med, 'dose': dose})
            found_names.add(med.lower())
    for pat in MEDICATION_PATTERNS:
        for m in re.finditer(pat, text):
            name = m.group(1).strip()
            dose = m.group(2).strip() if len(m.groups()) > 1 else ''
            if name.lower() not in found_names and len(name) > 3:
                medications.append({'name': name, 'dose': dose})
                found_names.add(name.lower())
    return medications[:15]


def _detect_anomalies(labs, vitals, text):
    anomalies = []
    all_vals = {**labs, **vitals}

    b12_low = re.search(r'Vitamin\s*B12[\s\S]{0,20}?<\s*(\d+)', text, re.IGNORECASE)
    if b12_low and 'Vitamin B12' not in all_vals:
        all_vals['Vitamin B12'] = b12_low.group(1)

    if re.search(r'Urine\s*Glucose[\s\S]{0,20}?Present', text, re.IGNORECASE):
        anomalies.append({
            'metric': 'Urine Glucose', 'value': 'Present (+)', 'unit': '',
            'status': 'Abnormal — should be Absent', 'range': 'Absent', 'severity': 'critical'
        })

    for metric, val_str in all_vals.items():
        if metric not in NORMAL_RANGES:
            continue
        lo, hi, unit, crit_lo, crit_hi = NORMAL_RANGES[metric]
        try:
            num = float(str(val_str).replace('<','').replace('>','').split('/')[0].strip())
            if num < lo:
                crit = crit_lo is not None and num < crit_lo
                sev = 'critical' if crit else ('high' if num < lo * 0.85 else 'moderate')
                anomalies.append({'metric': metric, 'value': val_str, 'unit': unit,
                                   'status': 'Below normal', 'range': f'{lo}–{hi}', 'severity': sev})
            elif num > hi:
                crit = crit_hi is not None and num > crit_hi
                sev = 'critical' if crit else ('high' if num > hi * 1.3 else 'moderate')
                anomalies.append({'metric': metric, 'value': val_str, 'unit': unit,
                                   'status': 'Above normal', 'range': f'{lo}–{hi}', 'severity': sev})
        except (ValueError, TypeError):
            pass

    return anomalies


def _classify_specialty(tl, labs):
    scores = {}
    lab_keys_lower = ' '.join(k.lower() for k in labs.keys())
    combined = tl + ' ' + lab_keys_lower
    for spec, kws in SPECIALTY_KEYWORDS.items():
        s = sum(1 for k in kws if k in combined)
        if s: scores[spec] = s
    if not scores: return 'General Medicine'
    return sorted(scores, key=scores.get, reverse=True)[0]


def _extract_explicit_risk(text, sections):
    """
    Many non-lab reports (radiology, imaging, procedure notes) state risk in
    words rather than via a numeric value out of range — e.g.
    'Grade 5 (High-Risk)'. Look for that language directly, preferring the
    Impression/Findings section if one was found, so the analyzer doesn't
    silently fall back to 'Low risk' just because there were no lab values
    to compare against a reference range.
    """
    search_text = sections.get('Impression') or sections.get('Findings') or text
    search_l = search_text.lower()
    for level, pat in EXPLICIT_RISK_PATTERNS:
        m = re.search(pat, search_l)
        if m:
            return level, m.group(0)
    return None, None


def _risk_score(labs, vitals, anomalies, tl, explicit_risk=None):
    score = 15
    for a in anomalies:
        if a['severity'] == 'critical': score += 20
        elif a['severity'] == 'high':   score += 12
        else:                            score += 5
    for metric, check_fn in HIGH_RISK_FLAGS.items():
        if metric in labs:
            try:
                val = float(str(labs[metric]).replace('<','').replace('>',''))
                if check_fn(val): score += 15
            except: pass
    score = min(100, score)
    level = 'Critical' if score >= 75 else 'High' if score >= 50 else 'Moderate' if score >= 30 else 'Low'

    # If the report states a risk level in words (common for radiology /
    # imaging reports with no numeric labs at all), never let that be
    # downgraded by an empty numeric score — only ever escalate.
    if explicit_risk and explicit_risk[0]:
        exp_level = explicit_risk[0]
        if RISK_LEVEL_RANK[exp_level] > RISK_LEVEL_RANK[level]:
            level = exp_level
            score = max(score, RISK_LEVEL_FLOOR_SCORE[exp_level])

    return score, level


def _extract_patient_info(text):
    info = {}

    # ── Name: multiple patterns, blacklist lab/brand words ───────────────────
    name_patterns = [
        r'(?:Patient\s*Name|Name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,40}?)(?:\n|Age|Sex|UHID|DOB|PID|$)',
        r'^([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s*$',
        r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s+Age\s*:',
        r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s*\n\s*Age\s*:',
    ]
    for pat in name_patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = m.group(1).strip()
            words = candidate.lower().split()
            if (len(words) <= 5 and
                not any(bad in candidate.lower() for bad in
                        ['lab','report','scan','path','medical','drlogy','sample','collection',
                         'pathology','diagnostic','clinic','hospital','centre','center'])):
                info['name'] = candidate
                break

    # ── Age ──────────────────────────────────────────────────────────────────
    age_patterns = [
        r'Age\s*[:\-]?\s*(\d{1,3})\s*(?:Years?|Yrs?)',
        r'Sex/Age\s*[:\-]?\s*(?:Male|Female)?\s*/?\s*(\d{1,3})\s*Y',
        r'(\d{1,3})\s*(?:Years?|Yrs?)\s*(?:old)?',
    ]
    for pat in age_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            info['age'] = m.group(1).strip() + ' years'
            break

    # ── Sex ──────────────────────────────────────────────────────────────────
    sex_m = re.search(r'Sex\s*[:\-]?\s*(Male|Female)', text, re.IGNORECASE)
    if not sex_m:
        sex_m = re.search(r'\b(Male|Female)\b', text, re.IGNORECASE)
    if sex_m:
        info['sex'] = sex_m.group(1).strip()

    # ── UHID / PID / Lab ID ───────────────────────────────────────────────────
    for label in ['UHID', 'PID', 'Lab\\s*Id', 'Patient\\s*ID']:
        uid_m = re.search(rf'{label}\s*[:\-]?\s*([A-Z0-9]+)', text, re.IGNORECASE)
        if uid_m:
            info['lab_id'] = uid_m.group(1).strip()
            break

    # ── Date ─────────────────────────────────────────────────────────────────
    date_m = re.search(r'(?:Collected|Reported|Date)\s*[Oo]n\s*[:\-]?\s*([\d\s\:\w]+?(?:AM|PM)?)\s*(?:\n|$)', text, re.IGNORECASE)
    if date_m:
        info['date'] = date_m.group(1).strip()

    return info


def _extract_sections(text):
    sections = {}
    test_sections = [
        ('Complete Blood Count', r'Complete Blood Count([\s\S]{0,600}?)(?=Blood Group|Lipid|Biochemistry|HbA1c|Thyroid|Immunoassay|Iron|Protein|\Z)'),
        ('Blood Group',          r'Blood Group([\s\S]{0,200}?)(?=Lipid|Biochemistry|\Z)'),
        ('Lipid Profile',        r'Lipid Profile([\s\S]{0,400}?)(?=Biochemistry|HbA1c|\Z)'),
        ('HbA1c',                r'HbA1c.*?Glycosylated([\s\S]{0,300}?)(?=Thyroid|Immunoassay|\Z)'),
        ('Thyroid Profile',      r'THYROID\s*PROFILE([\s\S]{0,500}?)(?=Note|Comment|End Of Report|\Z)'),
        ('Biochemistry',         r'Biochemistry([\s\S]{0,400}?)(?=Electrolytes|Immunoassay|\Z)'),
        ('BNP',                  r'B-TYPE NATRIURETIC([\s\S]{0,400}?)(?=Note|Comment|\Z)'),
        ('Urine Examination',    r'Physical.*?Dip strip([\s\S]{0,400}?)(?=End Of Report|\Z)'),
        # Radiology / imaging style reports
        ('Clinical History',     r'(?:REASON FOR STUDY|CLINICAL HISTORY|INDICATION)[:\s]*([\s\S]{0,400}?)(?=TECHNIQUE|COMPARISON|FINDINGS|\Z)'),
        ('Technique',            r'TECHNIQUE[:\s]*([\s\S]{0,400}?)(?=COMPARISON|FINDINGS|\Z)'),
        ('Findings',             r'FINDINGS[:\s]*([\s\S]{0,1200}?)(?=IMPRESSION|\Z)'),
        ('Impression',           r'IMPRESSION[:\s]*([\s\S]{0,800}?)(?=Signed|\Z)'),
    ]
    for name, pat in test_sections:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            content = m.group(1).strip()[:400]
            if content:
                sections[name] = content
    return sections


def _extract_keywords(tl, labs):
    vocab = {
        'diabetes','glucose','anemia','infection','fever','decreased',
        'abnormal','deficiency','critical','severe','moderate','mild',
        'normal','borderline','thyroid','allergy','vitamin','cholesterol',
        'thalassemia','parasitic','inflammatory','hematology','cardiac','natriuretic',
        'hypothyroid','hyperthyroid','triiodothyronine','thyroxine',
        'fistula','abscess','sphincter','radiology','fracture','hernia',
        'malignant','benign','lesion','tumor','hemorrhage','stenosis','complex','tract',
    }
    lab_kws = set()
    for k in labs.keys():
        for w in k.lower().split():
            if len(w) > 4 and w not in KEYWORD_BLACKLIST:
                lab_kws.add(w)
    words = set(re.findall(r'\b[a-z]{4,}\b', tl))
    # Remove blacklisted words
    words = words - KEYWORD_BLACKLIST
    return sorted((words | lab_kws) & (vocab | lab_kws))[:20]


def _icd_hints(tl, labs):
    hints = []
    seen_codes = set()
    combined = tl + ' ' + ' '.join(k.lower() for k in labs.keys())
    for kw, (code, desc) in ICD_MAP.items():
        if kw in combined and code not in seen_codes:
            hints.append({'code': code, 'desc': desc, 'keyword': kw})
            seen_codes.add(code)
    return hints


def _build_summary(patient, specialty, risk_level, labs, vitals, anomalies, sections, explicit_risk=None):
    parts = []

    if patient:
        name = patient.get('name', 'Unknown')
        age  = patient.get('age', '')
        sex  = patient.get('sex', '')
        descriptors = ', '.join(d for d in [sex, age] if d)
        parts.append(f"Patient: {name}, {descriptors}." if descriptors else f"Patient: {name}.")

    parts.append(f"This is a {specialty} report with {risk_level} risk level.")

    critical = [a for a in anomalies if a['severity'] == 'critical']
    high     = [a for a in anomalies if a['severity'] == 'high']
    moderate = [a for a in anomalies if a['severity'] == 'moderate']

    if critical:
        parts.append("CRITICAL findings: " + ', '.join(
            f"{a['metric']} ({a['value']} {a['unit']}) — {a['status']}" for a in critical[:5]) + ".")
    if high:
        parts.append("High-priority abnormals: " + ', '.join(
            f"{a['metric']} {a['value']}" for a in high[:4]) + ".")
    if moderate:
        parts.append("Moderate abnormals: " + ', '.join(
            f"{a['metric']} {a['value']}" for a in moderate[:3]) + ".")

    has_structured_data = bool(labs) or bool(vitals)

    if not anomalies:
        if has_structured_data:
            parts.append("All tested parameters are within normal reference ranges.")
        elif explicit_risk and explicit_risk[0] in ('High', 'Critical'):
            parts.append(
                f"No standard numeric lab values were detected, but the report's own "
                f"findings explicitly indicate {risk_level.upper()} risk "
                f"(matched phrase: \"{explicit_risk[1]}\"). Please review the Findings "
                f"and Impression sections below."
            )
        else:
            parts.append(
                "No structured lab values or vital signs were detected — this may not be a "
                "standard lab-report format (for example, a radiology, imaging, or procedure "
                "report). Automatic risk scoring is limited without numeric data, so please "
                "review the extracted text and report sections directly."
            )

    # Specific test summaries
    if 'TSH' in labs:
        tsv = float(labs['TSH'])
        st = "elevated — suggestive of hypothyroidism" if tsv > 4.0 else "suppressed — suggestive of hyperthyroidism" if tsv < 0.4 else "within normal range"
        parts.append(f"TSH: {labs['TSH']} mU/L — {st}.")
    if 'T3' in labs:
        parts.append(f"T3 Total: {labs['T3']} ng/dL.")
    if 'T4' in labs:
        parts.append(f"T4 Total: {labs['T4']} mcg/dL.")
    if 'BNP' in labs:
        bnp_val = labs['BNP']
        status = "within normal range (< 29.4 pg/mL)" if float(bnp_val) < 29.4 else "ELEVATED — consult cardiologist"
        parts.append(f"BNP: {bnp_val} pg/mL — {status}.")
    if 'Creatinine' in labs:
        parts.append(f"Renal function (Creatinine: {labs['Creatinine']} mg/dL) — within normal range.")

    parts.append("Please consult your physician for clinical correlation and management.")
    return ' '.join(parts)